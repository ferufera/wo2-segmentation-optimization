"""
select_evaluation_segments.py

This script creates a shortlist of real WO2Net segments for my thesis pilot
evaluation.

Why I need this:
    I do not want to choose pilot examples randomly or manually invent test
    cases. I want to use real segments from the WO2Net enriched segment data
    and real crowd validation feedback from the previous project.

Input:
    - enriched_segments.json
    - segment_validations.json

These files come from my previous WO2Net segmentation optimization work.

Output:
    - data/evaluation_segment_shortlist.json
    - data/evaluation_segment_shortlist.csv

The shortlist is not the final evaluation set yet. It is a candidate list from
which I can select around 5 real pilot segments for the next KG-RAG experiment.

Selection logic:
    The script prioritizes segments that are useful for testing concept linking:
    1. segments with removed concepts
    2. segments with comments mentioning missing concepts
    3. segments mentioning specific entities such as Westerbork, Reichenbach,
       Birkenau, Philips, Rotterdam, Meidagen, Sobibor, etc.
    4. segments with disagreement or mixed validation feedback
    5. accepted/control examples with mostly approved validation
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

CROWDSOURCE_DATA_DIR = Path(
    r"D:\Study\VU Amsterdam\Digital Humanities and Social Analytics in Practice\wo2-segmentation-optimization\data\crowdsource_data"
)

ENRICHED_FILE = CROWDSOURCE_DATA_DIR / "enriched_segments.json"
VALIDATIONS_FILE = CROWDSOURCE_DATA_DIR / "segment_validations.json"

BASE_DIR = Path(__file__).resolve().parents[1]

OUTPUT_JSON = BASE_DIR / "data" / "evaluation_segment_shortlist.json"
OUTPUT_CSV = BASE_DIR / "data" / "evaluation_segment_shortlist.csv"


# =============================================================================
# SETTINGS
# =============================================================================

CONSENSUS_THRESHOLD = 0.6

# These terms are based on issues seen in the previous crowdsource analysis.
# They are not final concepts. They are only used to find promising real examples.
SPECIFIC_ENTITY_KEYWORDS = [
    "Westerbork",
    "Sobibor",
    "Auschwitz",
    "Birkenau",
    "Reichenbach",
    "Reisenbach",
    "Bergen Belsen",
    "Bergen-Belsen",
    "Philips",
    "Telefunken",
    "Rotterdam",
    "Meidagen",
    "Hongerwinter",
    "Kristallnacht",
    "Kristalnacht",
    "Tilburg",
    "Den Bosch",
    "'s-Hertogenbosch",
    "Hollandsche Schouwburg",
    "Jodenster",
    "Onderduik",
    "Kinderbarak",
    "Diamantsnijders",
]


MISSING_CONCEPT_PATTERNS = [
    "ontbrekende concept",
    "ontbrekende concepten",
    "concept toevoegen",
    "concepten:",
    "ik mis",
    "mist",
    "ontbreekt",
]


# =============================================================================
# DATA LOADING
# =============================================================================

def load_json(path: Path):
    """
    Load a JSON file from disk.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def create_segment_map(enriched_data: list) -> dict:
    """
    Create a lookup dictionary from segment_id to the enriched segment object.

    The consolidated enriched_segments.json has this structure:
        [
          {
            "video_name": "...",
            "enriched_segments": [...]
          }
        ]

    This function flattens that structure.
    """
    segment_map = {}

    for video in enriched_data:
        video_name = video.get("video_name", "")
        segments = video.get("enriched_segments", [])

        if isinstance(segments, dict):
            segments = [segments]

        for segment in segments:
            if not isinstance(segment, dict):
                continue

            segment_id = segment.get("segment_id")

            if not segment_id:
                continue

            copied_segment = dict(segment)
            copied_segment["video_name"] = video_name

            segment_map[segment_id] = copied_segment

    return segment_map


def group_validations_by_segment(validations_data: list) -> dict:
    """
    Group all crowd validations by segment_id.

    Each segment can have multiple validations from different users.
    """
    grouped = defaultdict(list)

    for entry in validations_data:
        segment_id = entry.get("segment_id")
        validation = entry.get("segment_validation", {})

        if segment_id and validation:
            grouped[segment_id].append(validation)

    return grouped


# =============================================================================
# VALIDATION ANALYSIS
# =============================================================================

def is_clean_validation(validation: dict) -> bool:
    """
    Check whether one validation is a clean approval.

    A validation is clean if:
        - the fragment is not removed
        - title/start/end are approved
        - all concepts are kept
        - there is no substantial comment
    """
    if validation.get("remove_fragment") is True:
        return False

    if validation.get("title_validation", {}).get("decision") != "approve":
        return False

    if validation.get("start_time_validation", {}).get("decision") != "approve":
        return False

    if validation.get("end_time_validation", {}).get("decision") != "approve":
        return False

    for concept in validation.get("concept_validation", []):
        if concept.get("action") != "keep":
            return False

    comment = str(validation.get("comment", "")).strip()

    if comment:
        return False

    return True


def summarize_validations(validations: list) -> dict:
    """
    Summarize all validations for one segment.

    This creates the fields I need for choosing useful evaluation examples:
        - consensus status
        - number of clean vs non-clean validations
        - removed concepts
        - comments
        - issue types
    """
    total_votes = len(validations)

    if total_votes == 0:
        return {
            "consensus_status": "NO_VALIDATION",
            "total_votes": 0,
            "clean_votes": 0,
            "non_clean_votes": 0,
            "issue_counts": {},
            "removed_concepts": [],
            "comments": [],
            "missing_concept_comment": False,
        }

    clean_votes = sum(1 for validation in validations if is_clean_validation(validation))
    non_clean_votes = total_votes - clean_votes

    clean_ratio = clean_votes / total_votes
    non_clean_ratio = non_clean_votes / total_votes

    if clean_ratio >= CONSENSUS_THRESHOLD:
        consensus_status = "ACCEPTED"
    elif non_clean_ratio >= CONSENSUS_THRESHOLD:
        consensus_status = "REJECTED"
    else:
        consensus_status = "CONFLICT"

    issues = []
    removed_concepts = []
    comments = []

    for validation in validations:
        comment = str(validation.get("comment", "")).strip()

        if comment:
            comments.append(comment)

        if validation.get("remove_fragment") is True:
            issues.append("REMOVE_FRAGMENT")

        if validation.get("title_validation", {}).get("decision") == "edit":
            issues.append("EDIT_TITLE")

        if validation.get("start_time_validation", {}).get("decision") == "edit":
            issues.append("EDIT_START")

        if validation.get("end_time_validation", {}).get("decision") == "edit":
            issues.append("EDIT_END")

        for concept in validation.get("concept_validation", []):
            if concept.get("action") == "remove":
                issues.append("REMOVE_CONCEPT")
                removed_concepts.append(concept.get("uri", ""))

    joined_comments_lower = " ".join(comments).lower()

    missing_concept_comment = any(
        pattern in joined_comments_lower
        for pattern in MISSING_CONCEPT_PATTERNS
    )

    return {
        "consensus_status": consensus_status,
        "total_votes": total_votes,
        "clean_votes": clean_votes,
        "non_clean_votes": non_clean_votes,
        "issue_counts": dict(Counter(issues)),
        "removed_concepts": sorted(set(uri for uri in removed_concepts if uri)),
        "comments": comments,
        "missing_concept_comment": missing_concept_comment,
    }


# =============================================================================
# SHORTLIST SCORING
# =============================================================================

def find_keyword_hits(text: str, comments: list[str]) -> list[str]:
    """
    Find specific entity keywords in the segment text and validation comments.

    I look in both places because validators often mention missing concepts in
    comments, even when the current concept list does not contain them.
    """
    combined_text = f"{text} {' '.join(comments)}"
    hits = []

    for keyword in SPECIFIC_ENTITY_KEYWORDS:
        pattern = re.escape(keyword)
        if re.search(pattern, combined_text, flags=re.IGNORECASE):
            hits.append(keyword)

    return sorted(set(hits))


def score_segment(segment: dict, validation_summary: dict) -> tuple[int, list[str]]:
    """
    Assign a heuristic score to a segment for shortlist selection.

    Higher score means more useful for the pilot evaluation.
    The score is only used to create a shortlist, not to make final claims.
    """
    score = 0
    reasons = []

    issue_counts = validation_summary["issue_counts"]
    comments = validation_summary["comments"]
    text = segment.get("text", "")

    keyword_hits = find_keyword_hits(text, comments)

    if issue_counts.get("REMOVE_CONCEPT", 0) > 0:
        score += 5
        reasons.append("has_removed_concepts")

    if validation_summary["missing_concept_comment"]:
        score += 5
        reasons.append("has_missing_concept_comment")

    if keyword_hits:
        score += min(len(keyword_hits), 5)
        reasons.append("mentions_specific_entities")

    if validation_summary["consensus_status"] == "REJECTED":
        score += 3
        reasons.append("rejected_by_consensus")

    if validation_summary["consensus_status"] == "CONFLICT":
        score += 2
        reasons.append("conflict_case")

    if issue_counts.get("EDIT_TITLE", 0) > 0:
        score += 2
        reasons.append("title_edit_case")

    if issue_counts.get("EDIT_START", 0) > 0 or issue_counts.get("EDIT_END", 0) > 0:
        score += 1
        reasons.append("boundary_edit_case")

    if validation_summary["consensus_status"] == "ACCEPTED":
        score += 1
        reasons.append("possible_control_case")

    return score, sorted(set(reasons))


def get_original_concepts(segment: dict) -> list[dict]:
    """
    Extract the original matched concepts from the enriched segment.
    """
    concepts = []

    for concept in segment.get("matched_concepts", []):
        concepts.append({
            "uri": concept.get("uri", ""),
            "name": concept.get("name", ""),
            "source": concept.get("source", ""),
            "score": concept.get("score", ""),
        })

    return concepts


def build_shortlist(segment_map: dict, validation_map: dict) -> list[dict]:
    """
    Build a ranked shortlist of real segments for the pilot evaluation.
    """
    shortlist = []

    for segment_id, validations in validation_map.items():
        segment = segment_map.get(segment_id)

        if not segment:
            continue

        validation_summary = summarize_validations(validations)
        score, reasons = score_segment(segment, validation_summary)

        # Keep only useful candidates for the shortlist.
        # This prevents the file from becoming too large.
        if score < 4:
            continue

        comments = validation_summary["comments"]
        keyword_hits = find_keyword_hits(segment.get("text", ""), comments)

        shortlist.append({
            "segment_id": segment_id,
            "segment_title": segment.get("segment_title", ""),
            "interviewee_name": segment.get("interviewee_name", ""),
            "video_name": segment.get("video_name", ""),
            "start": segment.get("start"),
            "end": segment.get("end"),
            "duration": (
                round(segment.get("end", 0) - segment.get("start", 0), 2)
                if segment.get("start") is not None and segment.get("end") is not None
                else None
            ),
            "text": segment.get("text", ""),
            "original_matched_concepts": get_original_concepts(segment),
            "validation_summary": validation_summary,
            "keyword_hits": keyword_hits,
            "shortlist_score": score,
            "shortlist_reasons": reasons,
        })

    shortlist = sorted(
        shortlist,
        key=lambda item: (
            item["shortlist_score"],
            item["validation_summary"]["total_votes"]
        ),
        reverse=True
    )

    return shortlist


# =============================================================================
# OUTPUT
# =============================================================================

def save_shortlist_json(shortlist: list[dict]) -> None:
    """
    Save the full shortlist as JSON.
    """
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(shortlist, file, indent=2, ensure_ascii=False)

    print(f"Saved JSON shortlist: {OUTPUT_JSON}")


def save_shortlist_csv(shortlist: list[dict]) -> None:
    """
    Save a compact CSV version for easier manual inspection.
    """
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "segment_id",
        "segment_title",
        "interviewee_name",
        "consensus_status",
        "total_votes",
        "issue_counts",
        "keyword_hits",
        "shortlist_score",
        "shortlist_reasons",
        "text_preview",
        "comments_preview",
    ]

    rows = []

    for item in shortlist:
        validation_summary = item["validation_summary"]

        rows.append({
            "segment_id": item["segment_id"],
            "segment_title": item["segment_title"],
            "interviewee_name": item["interviewee_name"],
            "consensus_status": validation_summary["consensus_status"],
            "total_votes": validation_summary["total_votes"],
            "issue_counts": json.dumps(validation_summary["issue_counts"], ensure_ascii=False),
            "keyword_hits": " | ".join(item["keyword_hits"]),
            "shortlist_score": item["shortlist_score"],
            "shortlist_reasons": " | ".join(item["shortlist_reasons"]),
            "text_preview": item["text"][:250].replace("\n", " "),
            "comments_preview": " | ".join(validation_summary["comments"])[:250].replace("\n", " "),
        })

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved CSV shortlist: {OUTPUT_CSV}")


def print_summary(shortlist: list[dict]) -> None:
    """
    Print a short terminal summary after creating the shortlist.
    """
    print("\n" + "=" * 80)
    print("EVALUATION SEGMENT SHORTLIST SUMMARY")
    print("=" * 80)

    print(f"Shortlisted segments: {len(shortlist)}")

    status_counts = Counter(
        item["validation_summary"]["consensus_status"]
        for item in shortlist
    )

    print("\nConsensus status distribution:")
    for status, count in status_counts.most_common():
        print(f"- {status}: {count}")

    print("\nTop 10 candidate segments:")
    for index, item in enumerate(shortlist[:10], start=1):
        print("\n" + "-" * 80)
        print(f"{index}. {item['segment_id']}")
        print(f"Title: {item['segment_title']}")
        print(f"Score: {item['shortlist_score']}")
        print(f"Status: {item['validation_summary']['consensus_status']}")
        print(f"Reasons: {', '.join(item['shortlist_reasons'])}")
        print(f"Keyword hits: {', '.join(item['keyword_hits'])}")
        print(f"Comments: {' | '.join(item['validation_summary']['comments'])[:300]}")


def main() -> None:
    """
    Main script execution.
    """
    print("Loading real WO2Net data...")
    print(f"Enriched file: {ENRICHED_FILE}")
    print(f"Validations file: {VALIDATIONS_FILE}")

    enriched_data = load_json(ENRICHED_FILE)
    validations_data = load_json(VALIDATIONS_FILE)

    print("Creating segment and validation maps...")
    segment_map = create_segment_map(enriched_data)
    validation_map = group_validations_by_segment(validations_data)

    print(f"Loaded segments: {len(segment_map)}")
    print(f"Loaded validation groups: {len(validation_map)}")

    print("Building shortlist...")
    shortlist = build_shortlist(
        segment_map=segment_map,
        validation_map=validation_map
    )

    save_shortlist_json(shortlist)
    save_shortlist_csv(shortlist)
    print_summary(shortlist)


if __name__ == "__main__":
    main()