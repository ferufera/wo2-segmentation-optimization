"""
retrieve_candidates.py

This file contains the candidate retrieval logic for the KG-RAG thesis pipeline.

The goal of this stage is to retrieve relevant WO2 Thesaurus concepts for an
oral history segment before the LLM is asked to select the final concepts.

Retrieval layers:

1. Original matched concept seeds
   - Keeps concepts that the previous WO2Net pipeline already linked.
   - This prevents useful baseline concepts such as "Dwangarbeid" from being
     lost when they are not literally mentioned as exact thesaurus labels.

2. Explicit lexical retrieval
   - Finds concepts that are directly mentioned in the segment.
   - Example: "Rotterdam", "Kristallnacht", "Philips", "Reichenbach".

3. Contextual event retrieval
   - Finds event concepts that may be historically relevant even if the exact
     label is not literally mentioned.
   - Example: "mei 1940" + "Rotterdam" + "brand" can support candidates such as
     "Meidagen 1940" or "14 mei 1940".

4. Conservative event graph expansion
   - Adds only closely related event concepts from strong contextual events.
   - This step is intentionally conservative to avoid filling the prompt with
     unrelated events.

Important:
    This script does not decide the final concepts. It only prepares candidates.
    The LLM later decides which candidates are actually supported by the segment.

Why this matters:
    The retriever should be broad enough to include specific useful concepts,
    but not so broad that it fills the prompt with irrelevant concepts.
"""

import csv
import re
from typing import Dict, List, Optional, Tuple


URI_COL = "Concept URI"
ID_COL = "Concept ID"
LABEL_COL = "Name / Label"
TYPE_COL = "Concept Type"
BROADER_COL = "Broader Concepts"
NARROWER_COL = "Narrower Concepts"
RELATED_COL = "Related Concepts"
SCHEME_COL = "In Scheme"

EVENT_SCHEME_ID = "4329"


DUTCH_STOPWORDS = {
    "de", "het", "een", "en", "of", "van", "voor", "in", "op", "aan",
    "met", "te", "bij", "door", "naar", "over", "uit", "als", "dat",
    "die", "dit", "zijn", "haar", "hun", "ik", "je", "hij", "zij",
    "we", "wij", "ze", "was", "waren", "werd", "wordt", "had", "heb",
    "mijn", "ook", "maar", "dan", "toen", "hoe", "wel", "niet", "geen",
    "daar", "hier", "dus", "nou", "ja", "nee", "hem", "ons", "onze",
    "u", "uw", "deze", "wat", "waar", "wie", "waarom", "wanneer",
    "moet", "moesten", "kon", "konden", "gaan", "ging", "gingen",
    "komen", "kwam", "kwamen"
}


MONTH_ALIASES = {
    "january": {"januari", "jan", "january", "januar"},
    "february": {"februari", "feb", "february", "februar"},
    "march": {"maart", "march", "märz", "marz"},
    "april": {"april", "apr"},
    "may": {"mei", "may", "mai"},
    "june": {"juni", "june", "jun"},
    "july": {"juli", "july", "jul"},
    "august": {"augustus", "august", "aug"},
    "september": {"september", "sep"},
    "october": {"oktober", "october", "okt", "oct"},
    "november": {"november", "nov"},
    "december": {"december", "dezember", "dec", "dez"},
}


GENERIC_ONE_WORD_LABELS = {
    "af", "bestuur", "borden", "meisjes", "gebouwen", "verliezen",
    "rampen", "vlaggen", "eten", "kinderen", "toerisme", "portretten",
    "woningen", "transport", "kampen", "geboren", "verhuisd",
    "overleden", "joden", "cross", "arbeit", "meer", "heel",
    "contact", "holland", "duitsland", "bezetting"
}


IMPORTANT_ONE_WORD_LABELS = {
    "auschwitz", "sobibor", "westerbork", "birkenau", "reichenbach",
    "kristallnacht", "philips", "rotterdam", "amsterdam", "vught",
    "belsen", "theresienstadt", "monowitz", "buchenwald"
}


def split_pipe(value: str) -> List[str]:
    """
    Split pipe-separated values from the CSV.
    """
    if not value:
        return []

    return [
        part.strip().strip("'").strip()
        for part in str(value).split("|")
        if part.strip()
    ]


def normalize(text: str) -> str:
    """
    Normalize text for matching.
    """
    text = text.lower()
    text = re.sub(r"[^a-zA-Z0-9À-ÿ\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(text: str) -> set:
    """
    Convert text into useful tokens.
    """
    tokens = normalize(text).split()
    useful_tokens = set()

    for token in tokens:
        if token in DUTCH_STOPWORDS:
            continue

        if token.isdigit():
            useful_tokens.add(token)
            continue

        if len(token) > 2:
            useful_tokens.add(token)

    return useful_tokens


def contains_exact_phrase(label_norm: str, segment_norm: str) -> bool:
    """
    Check whether a normalized label occurs as a real phrase.
    """
    if not label_norm:
        return False

    pattern = r"(?<!\w)" + re.escape(label_norm) + r"(?!\w)"
    return re.search(pattern, segment_norm) is not None


def is_year_token(token: str) -> bool:
    """
    Check whether a token looks like a year.
    """
    return token.isdigit() and len(token) == 4


def extract_month_keys(tokens: set) -> set:
    """
    Detect month references in a set of tokens.
    """
    found_months = set()

    for token in tokens:
        for month_key, aliases in MONTH_ALIASES.items():
            if token in aliases:
                found_months.add(month_key)

    return found_months


def has_month_compound_match(label_tokens: set, segment_tokens: set) -> bool:
    """
    Check whether a month in the segment supports a compound month expression.
    """
    segment_months = extract_month_keys(segment_tokens)

    if not segment_months:
        return False

    for label_token in label_tokens:
        for month_key in segment_months:
            aliases = MONTH_ALIASES[month_key]

            for alias in aliases:
                if label_token.startswith(alias) and len(label_token) > len(alias):
                    return True

    return False


def has_conflicting_months(label_tokens: set, segment_tokens: set) -> bool:
    """
    Check whether the concept label and segment mention different months.
    """
    label_months = extract_month_keys(label_tokens)
    segment_months = extract_month_keys(segment_tokens)

    if not label_months or not segment_months:
        return False

    return label_months.isdisjoint(segment_months)


def all_month_aliases() -> set:
    """
    Return all month words from the alias dictionary.
    """
    aliases = set()

    for alias_set in MONTH_ALIASES.values():
        aliases.update(alias_set)

    return aliases


def is_event_concept(concept: dict) -> bool:
    """
    Check whether a concept should be treated as an event candidate.
    """
    uri = concept.get("uri", "")
    types = concept.get("types", [])
    schemes = concept.get("schemes", [])

    return (
        "/events/" in uri
        or "Event" in types
        or EVENT_SCHEME_ID in schemes
    )


def is_location_or_named_entity(types: List[str], uri: str) -> bool:
    """
    Check whether a concept is likely a named entity/location/camp/organisation.
    """
    return (
        "SpatialThing" in types
        or "/locations/" in uri
        or "/kampen/" in uri
        or "/corporaties/" in uri
        or "/personen/" in uri
    )


def canonical_label(concept: dict, matched_label: Optional[str] = None) -> str:
    """
    Choose a readable label to show in candidate outputs.

    Some concepts have alternative labels where the matched label may be partial
    or less readable, for example "Belsen" for the Bergen-Belsen concept.
    """
    labels = concept.get("labels", [])

    if not labels:
        return matched_label or ""

    for label in labels:
        if "bergen" in normalize(label) and "belsen" in normalize(label):
            return label

    clean_labels = [label for label in labels if label.strip()]

    if not clean_labels:
        return matched_label or ""

    if matched_label:
        matched_norm = normalize(matched_label)

        if matched_norm in IMPORTANT_ONE_WORD_LABELS:
            return matched_label

        if len(matched_label.split()) >= 2:
            return matched_label

    return sorted(clean_labels, key=len, reverse=True)[0]


def is_label_too_weak(
    label: str,
    types: Optional[List[str]] = None,
    uri: str = ""
) -> bool:
    """
    Filter out labels that are too weak for reliable explicit retrieval.
    """
    types = types or []
    tokens = normalize(label).split()

    if not tokens:
        return True

    if len(tokens) == 1:
        token = tokens[0]
        original = label.strip()

        if token in IMPORTANT_ONE_WORD_LABELS:
            return False

        if token in DUTCH_STOPWORDS:
            return True

        if token in GENERIC_ONE_WORD_LABELS and not is_location_or_named_entity(types, uri):
            return True

        if len(token) <= 3 and not original.isupper():
            return True

    return False


def one_word_label_score(
    label: str,
    segment_text: str,
    types: List[str],
    uri: str
) -> float:
    """
    Score one-word labels for explicit retrieval.
    """
    label_norm = normalize(label)
    segment_norm = normalize(segment_text)

    if not contains_exact_phrase(label_norm, segment_norm):
        return 0.0

    is_spatial = "SpatialThing" in types
    is_capitalized_label = label[:1].isupper()

    if is_spatial and is_capitalized_label:
        pattern = r"(?<!\w)" + re.escape(label) + r"(?!\w)"
        if not re.search(pattern, segment_text):
            return 0.0

    if label_norm in IMPORTANT_ONE_WORD_LABELS:
        return 100.0

    if label_norm in GENERIC_ONE_WORD_LABELS and not is_location_or_named_entity(types, uri):
        return 0.0

    return 100.0


def multi_word_label_score(label: str, segment_text: str) -> float:
    """
    Score multi-word labels for explicit retrieval.
    """
    label_norm = normalize(label)
    segment_norm = normalize(segment_text)

    if label_norm and contains_exact_phrase(label_norm, segment_norm):
        return 100.0

    label_tokens = token_set(label)
    segment_tokens = token_set(segment_text)

    if not label_tokens:
        return 0.0

    overlap_tokens = label_tokens.intersection(segment_tokens)
    overlap_count = len(overlap_tokens)
    overlap_ratio = overlap_count / len(label_tokens)

    if overlap_count < 2:
        return 0.0

    label_year_tokens = {token for token in label_tokens if is_year_token(token)}
    segment_year_tokens = {token for token in segment_tokens if is_year_token(token)}

    if label_year_tokens and not label_year_tokens.issubset(segment_year_tokens):
        return 0.0

    if has_conflicting_months(label_tokens, segment_tokens):
        return 0.0

    if overlap_ratio < 0.5:
        return 0.0

    return round(overlap_ratio * 100, 2)


def lexical_score(
    label: str,
    segment_text: str,
    types: List[str],
    uri: str = ""
) -> float:
    """
    Score how well a thesaurus label explicitly matches the segment.
    """
    if is_label_too_weak(label, types=types, uri=uri):
        return 0.0

    label_tokens_raw = normalize(label).split()

    if len(label_tokens_raw) == 1:
        return one_word_label_score(label, segment_text, types, uri)

    return multi_word_label_score(label, segment_text)


def load_thesaurus(csv_path: str) -> Tuple[Dict[str, dict], List[dict]]:
    """
    Load the flattened WO2 Thesaurus CSV.
    """
    concepts_by_id = {}
    searchable_labels = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            uri = row.get(URI_COL, "").strip()
            concept_id = row.get(ID_COL, "").strip()

            if not uri or not concept_id:
                continue

            labels = split_pipe(row.get(LABEL_COL, ""))
            types = split_pipe(row.get(TYPE_COL, ""))

            concept = {
                "concept_id": concept_id,
                "uri": uri,
                "labels": labels,
                "types": types,
                "schemes": split_pipe(row.get(SCHEME_COL, "")),
                "broader_ids": split_pipe(row.get(BROADER_COL, "")),
                "narrower_ids": split_pipe(row.get(NARROWER_COL, "")),
                "related_ids": split_pipe(row.get(RELATED_COL, "")),
            }

            concepts_by_id[concept_id] = concept

            for label in labels:
                searchable_labels.append({
                    "concept_id": concept_id,
                    "uri": uri,
                    "label": label,
                    "types": types,
                    "schemes": concept["schemes"],
                })

    return concepts_by_id, searchable_labels


def find_concept_by_uri(
    concepts_by_id: Dict[str, dict],
    uri: str
) -> Optional[dict]:
    """
    Find a thesaurus concept by URI.
    """
    for concept in concepts_by_id.values():
        if concept.get("uri") == uri:
            return concept

    return None


def original_matched_concept_candidates(
    original_matched_concepts: Optional[List[dict]],
    concepts_by_id: Dict[str, dict]
) -> List[dict]:
    """
    Convert original WO2Net matched concepts into retrieval candidates.
    """
    if not original_matched_concepts:
        return []

    candidates = []

    for original in original_matched_concepts:
        uri = original.get("uri", "").strip()
        original_name = original.get("name", "").strip()

        if not uri:
            continue

        concept = find_concept_by_uri(concepts_by_id, uri)

        if concept is None:
            candidates.append({
                "concept_id": uri.rsplit("/", 1)[-1],
                "uri": uri,
                "label": original_name,
                "all_labels": [original_name] if original_name else [],
                "types": [],
                "schemes": [],
                "broader_ids": [],
                "narrower_ids": [],
                "related_ids": [],
                "retrieval_score": 88.0,
                "retrieval_reason": "original WO2Net matched concept seed",
                "candidate_source": "original_seed"
            })
            continue

        label = canonical_label(concept, matched_label=original_name)

        candidates.append({
            "concept_id": concept["concept_id"],
            "uri": concept["uri"],
            "label": label,
            "all_labels": concept["labels"],
            "types": concept["types"],
            "schemes": concept["schemes"],
            "broader_ids": concept["broader_ids"],
            "narrower_ids": concept["narrower_ids"],
            "related_ids": concept["related_ids"],
            "retrieval_score": 88.0,
            "retrieval_reason": "original WO2Net matched concept seed",
            "candidate_source": "original_seed"
        })

    return candidates


def retrieve_explicit_candidates(
    segment_text: str,
    concepts_by_id: Dict[str, dict],
    searchable_labels: List[dict],
    threshold: float = 70.0
) -> List[dict]:
    """
    Retrieve concepts that are explicitly mentioned in the segment.
    """
    best_by_concept = {}

    for item in searchable_labels:
        label = item["label"]
        types = item.get("types", [])
        uri = item.get("uri", "")

        score = lexical_score(label, segment_text, types, uri=uri)

        if score < threshold:
            continue

        concept_id = item["concept_id"]
        concept = concepts_by_id[concept_id]
        display_label = canonical_label(concept, matched_label=label)

        if (
            concept_id not in best_by_concept
            or score > best_by_concept[concept_id]["retrieval_score"]
        ):
            best_by_concept[concept_id] = {
                "concept_id": concept_id,
                "uri": concept["uri"],
                "label": display_label,
                "matched_label": label,
                "all_labels": concept["labels"],
                "types": concept["types"],
                "schemes": concept["schemes"],
                "broader_ids": concept["broader_ids"],
                "narrower_ids": concept["narrower_ids"],
                "related_ids": concept["related_ids"],
                "retrieval_score": round(score, 2),
                "retrieval_reason": "explicit lexical match",
                "candidate_source": "explicit"
            }

    return sorted(
        best_by_concept.values(),
        key=lambda item: item["retrieval_score"],
        reverse=True
    )


def get_explicit_location_tokens(explicit_candidates: List[dict]) -> set:
    """
    Extract explicitly mentioned location tokens from explicit candidates.
    """
    location_tokens = set()

    for candidate in explicit_candidates:
        if not is_location_or_named_entity(
            candidate.get("types", []),
            candidate.get("uri", "")
        ):
            continue

        for label in candidate.get("all_labels", []):
            tokens = token_set(label)

            if len(tokens) == 1:
                location_tokens.update(tokens)

    return location_tokens


def is_place_specific_bombardment_without_matching_location(
    concept: dict,
    location_tokens: set
) -> bool:
    """
    Avoid retrieving place-specific bombardments for the wrong place.
    """
    if not location_tokens:
        return False

    all_labels_text = " ".join(concept.get("labels", []))
    all_labels_norm = normalize(all_labels_text)
    all_label_tokens = token_set(all_labels_text)

    is_place_specific_bombardment = (
        "bombardement op" in all_labels_norm
        or "bombing of" in all_labels_norm
        or "bombardierung von" in all_labels_norm
    )

    if not is_place_specific_bombardment:
        return False

    return not bool(location_tokens.intersection(all_label_tokens))


def contextual_event_score(
    concept: dict,
    segment_text: str,
    location_tokens: set
) -> Tuple[float, str]:
    """
    Score an event concept as a contextual candidate.
    """
    if is_place_specific_bombardment_without_matching_location(concept, location_tokens):
        return 0.0, ""

    segment_tokens = token_set(segment_text)
    month_alias_tokens = all_month_aliases()

    best_score = 0.0
    best_label = ""

    all_labels_text = " ".join(concept.get("labels", []))
    all_label_tokens = token_set(all_labels_text)

    concept_has_location_overlap = bool(location_tokens.intersection(all_label_tokens))

    for label in concept.get("labels", []):
        label_norm = normalize(label)
        segment_norm = normalize(segment_text)

        if label_norm and contains_exact_phrase(label_norm, segment_norm):
            score = 100.0
        else:
            label_tokens = token_set(label)

            if not label_tokens:
                continue

            if has_conflicting_months(label_tokens, segment_tokens):
                continue

            overlap_tokens = label_tokens.intersection(segment_tokens)

            label_year_tokens = {
                token for token in label_tokens
                if is_year_token(token)
            }
            segment_year_tokens = {
                token for token in segment_tokens
                if is_year_token(token)
            }

            year_overlap = len(label_year_tokens.intersection(segment_year_tokens))

            non_date_overlap = {
                token for token in overlap_tokens
                if not is_year_token(token)
                and token not in month_alias_tokens
            }

            month_period_match = has_month_compound_match(
                label_tokens=label_tokens,
                segment_tokens=segment_tokens
            )

            has_bombardment_label = any(
                token.startswith("bombard")
                for token in label_tokens
            )

            has_bombing_context = bool({
                "brand", "branden", "bombardement",
                "bombarderen", "luchtalarm", "vliegtuigen"
            }.intersection(segment_tokens))

            score = 0.0

            if year_overlap:
                score += 35

            if month_period_match:
                score += 25

            if concept_has_location_overlap:
                score += 25

            if non_date_overlap:
                score += min(len(non_date_overlap), 2) * 20

            if has_bombardment_label and has_bombing_context:
                score += 20

            if (
                not non_date_overlap
                and not concept_has_location_overlap
                and not month_period_match
                and not (has_bombardment_label and has_bombing_context)
            ):
                score = 0.0

        score = min(score, 100.0)

        if score > best_score:
            best_score = score
            best_label = label

    return best_score, best_label


def retrieve_contextual_event_candidates(
    segment_text: str,
    concepts_by_id: Dict[str, dict],
    explicit_candidates: List[dict],
    threshold: float = 75.0,
    top_k: int = 10
) -> List[dict]:
    """
    Retrieve possible event candidates that are contextually relevant.
    """
    location_tokens = get_explicit_location_tokens(explicit_candidates)
    contextual_candidates = []

    for concept in concepts_by_id.values():
        if not is_event_concept(concept):
            continue

        score, best_label = contextual_event_score(
            concept=concept,
            segment_text=segment_text,
            location_tokens=location_tokens
        )

        if score < threshold:
            continue

        display_label = canonical_label(concept, matched_label=best_label)

        contextual_candidates.append({
            "concept_id": concept["concept_id"],
            "uri": concept["uri"],
            "label": display_label,
            "matched_label": best_label,
            "all_labels": concept["labels"],
            "types": concept["types"],
            "schemes": concept["schemes"],
            "broader_ids": concept["broader_ids"],
            "narrower_ids": concept["narrower_ids"],
            "related_ids": concept["related_ids"],
            "retrieval_score": round(score, 2),
            "retrieval_reason": "contextual event retrieval",
            "candidate_source": "contextual_event"
        })

    return sorted(
        contextual_candidates,
        key=lambda item: item["retrieval_score"],
        reverse=True
    )[:top_k]


def add_event_graph_expansion(
    candidates: List[dict],
    concepts_by_id: Dict[str, dict],
    max_new: int = 5
) -> List[dict]:
    """
    Add related and broader event concepts from the strongest contextual events.
    """
    existing_ids = {candidate["concept_id"] for candidate in candidates}
    expanded = list(candidates)
    added_count = 0

    seed_candidates = [
        candidate for candidate in candidates
        if candidate.get("candidate_source") == "contextual_event"
        and candidate.get("retrieval_score", 0) >= 90
    ][:3]

    for candidate in seed_candidates:
        if added_count >= max_new:
            break

        neighbor_ids = []
        neighbor_ids.extend(candidate.get("related_ids", []))
        neighbor_ids.extend(candidate.get("broader_ids", []))

        for neighbor_id in neighbor_ids:
            if added_count >= max_new:
                break

            if neighbor_id in existing_ids:
                continue

            if neighbor_id not in concepts_by_id:
                continue

            neighbor = concepts_by_id[neighbor_id]

            if not is_event_concept(neighbor):
                continue

            if not neighbor.get("labels"):
                continue

            expanded.append({
                "concept_id": neighbor_id,
                "uri": neighbor["uri"],
                "label": canonical_label(neighbor),
                "all_labels": neighbor["labels"],
                "types": neighbor["types"],
                "schemes": neighbor["schemes"],
                "broader_ids": neighbor["broader_ids"],
                "narrower_ids": neighbor["narrower_ids"],
                "related_ids": neighbor["related_ids"],
                "retrieval_score": round(max(candidate["retrieval_score"] - 12, 50), 2),
                "retrieval_reason": f"conservative event graph expansion from {candidate['label']}",
                "candidate_source": "event_graph_expansion"
            })

            existing_ids.add(neighbor_id)
            added_count += 1

    return expanded


def merge_candidates(candidate_lists: List[List[dict]], top_k: int = 40) -> List[dict]:
    """
    Merge candidates from several retrieval layers.
    """
    best_by_concept = {}

    source_priority = {
        "explicit": 4,
        "original_seed": 3,
        "contextual_event": 2,
        "event_graph_expansion": 1
    }

    for candidate_list in candidate_lists:
        for candidate in candidate_list:
            concept_id = candidate["concept_id"]

            if concept_id not in best_by_concept:
                best_by_concept[concept_id] = candidate
                continue

            current = best_by_concept[concept_id]

            candidate_key = (
                candidate.get("retrieval_score", 0),
                source_priority.get(candidate.get("candidate_source", ""), 0)
            )

            current_key = (
                current.get("retrieval_score", 0),
                source_priority.get(current.get("candidate_source", ""), 0)
            )

            if candidate_key > current_key:
                best_by_concept[concept_id] = candidate

    return sorted(
        best_by_concept.values(),
        key=lambda item: (
            item.get("retrieval_score", 0),
            source_priority.get(item.get("candidate_source", ""), 0)
        ),
        reverse=True
    )[:top_k]


def retrieve_candidates(
    segment_text: str,
    concepts_by_id: Dict[str, dict],
    searchable_labels: List[dict],
    top_k: int = 40,
    explicit_threshold: float = 70.0,
    contextual_event_threshold: float = 75.0,
    include_contextual_events: bool = True,
    include_event_graph: bool = True,
    original_matched_concepts: Optional[List[dict]] = None
) -> List[dict]:
    """
    Retrieve candidate WO2 Thesaurus concepts for one segment.
    """
    original_seed_candidates = original_matched_concept_candidates(
        original_matched_concepts=original_matched_concepts,
        concepts_by_id=concepts_by_id
    )

    explicit_candidates = retrieve_explicit_candidates(
        segment_text=segment_text,
        concepts_by_id=concepts_by_id,
        searchable_labels=searchable_labels,
        threshold=explicit_threshold
    )

    contextual_candidates = []

    if include_contextual_events:
        contextual_candidates = retrieve_contextual_event_candidates(
            segment_text=segment_text,
            concepts_by_id=concepts_by_id,
            explicit_candidates=explicit_candidates,
            threshold=contextual_event_threshold,
            top_k=10
        )

        if include_event_graph:
            contextual_candidates = add_event_graph_expansion(
                candidates=contextual_candidates,
                concepts_by_id=concepts_by_id,
                max_new=5
            )

    return merge_candidates(
        candidate_lists=[
            explicit_candidates,
            original_seed_candidates,
            contextual_candidates
        ],
        top_k=top_k
    )


if __name__ == "__main__":
    print(
        "This file defines retrieval functions. "
        "Run 04_run_candidate_retrieval.py to test retrieval and save outputs."
    )