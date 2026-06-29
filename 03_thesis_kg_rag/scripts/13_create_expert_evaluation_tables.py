"""
13_create_expert_evaluation_tables.py

Step 13 of the KG-RAG thesis pipeline.

This script creates expert evaluation tables from the outputs of the three
concept-linking conditions:

1. Baseline prompting
2. Refined prompting
3. KG-RAG prompting

Inputs:
    data/evaluation_segments.json
    results/llm_outputs/baseline_cleaned/
    results/llm_outputs/refined_cleaned/
    results/llm_outputs/kg_rag_cleaned/

Outputs:
    results/expert_evaluation/internal_expert_evaluation_table.csv
    results/expert_evaluation/expert_evaluation_table.csv

Why I do this:
    The expert evaluation should show historians one combined list of proposed
    concepts per segment, without revealing which method selected each concept.

    The internal table keeps method provenance so the ratings can later be
    mapped back to baseline, refined, and KG-RAG.

    The expert-facing table hides method provenance to reduce bias.
"""

import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

EVALUATION_SEGMENTS_JSON = BASE_DIR / "data" / "evaluation_segments.json"

BASELINE_DIR = BASE_DIR / "results" / "llm_outputs" / "baseline_cleaned"
REFINED_DIR = BASE_DIR / "results" / "llm_outputs" / "refined_cleaned"
KG_RAG_DIR = BASE_DIR / "results" / "llm_outputs" / "kg_rag_cleaned"

OUTPUT_DIR = BASE_DIR / "results" / "expert_evaluation"

INTERNAL_OUTPUT_CSV = OUTPUT_DIR / "internal_expert_evaluation_table.csv"
EXPERT_OUTPUT_CSV = OUTPUT_DIR / "expert_evaluation_table.csv"


PILOT_METADATA = {
    "02%20stiso_20091008_Huffener_Lotty_1.nl_8": {
        "case_id": "case_01",
        "pilot_role": "organisation_work_conflict_case"
    },
    "01_JKKV_2003_LOTTY_HUFFENER-Veffer-h264.nl_1": {
        "case_id": "case_02",
        "pilot_role": "missing_camp_concepts_case"
    },
    "04_JKKV_2003_ANNIE_SULZBACH-h264.nl_3": {
        "case_id": "case_03",
        "pilot_role": "missing_event_concept_case"
    },
    "08%20stiso_20091104_Wurms_Rob_1.nl_10": {
        "case_id": "case_04",
        "pilot_role": "accepted_control_case"
    },
    "22%20stiso_20110501_Zeehandelaar_Geertruida_1.nl_4": {
        "case_id": "case_05",
        "pilot_role": "specific_place_disambiguation_case"
    }
}


EXPECTED_SEGMENTS = list(PILOT_METADATA.keys())


def safe_filename(segment_id: str) -> str:
    """
    Convert a segment ID into the filename-safe version used in output files.
    """
    return (
        segment_id
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("%20", "_")
        .replace(" ", "_")
    )


def load_json(path: Path):
    """
    Load a JSON file.
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing expected file:\n{path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_evaluation_segments() -> dict:
    """
    Load evaluation segments and index them by segment ID.
    """
    segments = load_json(EVALUATION_SEGMENTS_JSON)

    return {
        segment["segment_id"]: segment
        for segment in segments
    }


def get_segment_text(segment: dict) -> str:
    """
    Extract segment text from the evaluation segment object.
    """
    return segment.get("text", "").replace("\n", " ").strip()


def create_short_excerpt(text: str, max_chars: int = 900) -> str:
    """
    Create a short excerpt for expert evaluation.

    The excerpt is long enough to give context, but short enough to keep the
    table manageable.
    """
    text = " ".join(text.split())

    if len(text) <= max_chars:
        return text

    return text[:max_chars].rstrip() + " [...]"


def get_baseline_output_path(segment_id: str) -> Path:
    safe_id = safe_filename(segment_id)
    return BASELINE_DIR / f"{safe_id}_baseline_output_cleaned.json"


def get_refined_output_path(segment_id: str) -> Path:
    safe_id = safe_filename(segment_id)
    return REFINED_DIR / f"{safe_id}_refined_output_cleaned.json"


def get_kg_rag_output_path(segment_id: str) -> Path:
    safe_id = safe_filename(segment_id)
    return KG_RAG_DIR / f"{safe_id}_kg_rag_output_cleaned.json"


def extract_baseline_or_refined_concepts(output: list[dict]) -> list[dict]:
    """
    Extract concepts from baseline/refined output.

    Expected format:
    [
      {"concept": "Auschwitz", "score": 0.99}
    ]
    """
    concepts = []

    for item in output:
        label = item.get("concept", "").strip()

        if not label:
            continue

        concepts.append({
            "label": label,
            "uri": "",
            "score": item.get("score", "")
        })

    return concepts


def extract_kg_rag_concepts(output: dict) -> list[dict]:
    """
    Extract concepts from KG-RAG output.

    Expected format:
    {
      "selected_concepts": [
        {"label": "Auschwitz", "uri": "...", "confidence": 0.99}
      ]
    }
    """
    concepts = []

    for item in output.get("selected_concepts", []):
        label = item.get("label", "").strip()

        if not label:
            continue

        concepts.append({
            "label": label,
            "uri": item.get("uri", "").strip(),
            "score": item.get("confidence", "")
        })

    return concepts


def extract_original_concept_uri_map(segment: dict) -> dict:
    """
    Extract a label-to-URI mapping from original WO2Net matched concepts.

    This is useful because baseline and refined outputs usually only contain
    labels, while KG-RAG outputs contain URIs.

    The function is intentionally robust because different files may use
    slightly different key names.
    """
    uri_map = {}

    for concept in segment.get("original_matched_concepts", []):
        label = (
            concept.get("name")
            or concept.get("label")
            or concept.get("concept")
            or ""
        ).strip()

        uri = (
            concept.get("uri")
            or concept.get("concept_uri")
            or concept.get("url")
            or concept.get("id")
            or ""
        )

        if label and uri:
            uri_map[label] = str(uri).strip()

    return uri_map


def add_concepts_to_combined_map(
    combined: dict,
    concepts: list[dict],
    method_name: str,
    uri_fallback_map: dict
) -> None:
    """
    Add concepts from one method to the combined concept map.

    Concepts are combined by label. This keeps the expert table readable.
    Method provenance is stored in the internal version only.
    """
    for concept in concepts:
        label = concept["label"]
        uri = concept.get("uri", "") or uri_fallback_map.get(label, "")

        if label not in combined:
            combined[label] = {
                "concept_label": label,
                "concept_uri": uri,
                "selected_by_baseline": False,
                "selected_by_refined": False,
                "selected_by_kg_rag": False,
                "baseline_score": "",
                "refined_score": "",
                "kg_rag_score": ""
            }

        if uri and not combined[label]["concept_uri"]:
            combined[label]["concept_uri"] = uri

        if method_name == "baseline":
            combined[label]["selected_by_baseline"] = True
            combined[label]["baseline_score"] = concept.get("score", "")

        elif method_name == "refined":
            combined[label]["selected_by_refined"] = True
            combined[label]["refined_score"] = concept.get("score", "")

        elif method_name == "kg_rag":
            combined[label]["selected_by_kg_rag"] = True
            combined[label]["kg_rag_score"] = concept.get("score", "")


def build_rows_for_segment(segment_id: str, segment: dict) -> list[dict]:
    """
    Build expert evaluation rows for one segment.
    """
    baseline_output = load_json(get_baseline_output_path(segment_id))
    refined_output = load_json(get_refined_output_path(segment_id))
    kg_rag_output = load_json(get_kg_rag_output_path(segment_id))

    baseline_concepts = extract_baseline_or_refined_concepts(baseline_output)
    refined_concepts = extract_baseline_or_refined_concepts(refined_output)
    kg_rag_concepts = extract_kg_rag_concepts(kg_rag_output)

    uri_fallback_map = extract_original_concept_uri_map(segment)

    combined = {}

    add_concepts_to_combined_map(
        combined=combined,
        concepts=baseline_concepts,
        method_name="baseline",
        uri_fallback_map=uri_fallback_map
    )

    add_concepts_to_combined_map(
        combined=combined,
        concepts=refined_concepts,
        method_name="refined",
        uri_fallback_map=uri_fallback_map
    )

    add_concepts_to_combined_map(
        combined=combined,
        concepts=kg_rag_concepts,
        method_name="kg_rag",
        uri_fallback_map=uri_fallback_map
    )

    metadata = PILOT_METADATA[segment_id]
    segment_text = get_segment_text(segment)
    segment_excerpt = create_short_excerpt(segment_text)

    rows = []

    for index, concept_data in enumerate(sorted(combined.values(), key=lambda x: x["concept_label"].lower()), start=1):
        rows.append({
            "case_id": metadata["case_id"],
            "concept_id": f"{metadata['case_id']}_concept_{index:02d}",
            "segment_id": segment_id,
            "pilot_role": metadata["pilot_role"],
            "segment_excerpt": segment_excerpt,
            "concept_label": concept_data["concept_label"],
            "concept_uri": concept_data["concept_uri"],
            "selected_by_baseline": concept_data["selected_by_baseline"],
            "selected_by_refined": concept_data["selected_by_refined"],
            "selected_by_kg_rag": concept_data["selected_by_kg_rag"],
            "baseline_score": concept_data["baseline_score"],
            "refined_score": concept_data["refined_score"],
            "kg_rag_score": concept_data["kg_rag_score"],
            "correctness": "",
            "specificity": "",
            "missing_concept_comment": "",
            "general_comment": ""
        })

    return rows


def save_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    """
    Save rows to CSV.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def create_expert_facing_rows(internal_rows: list[dict]) -> list[dict]:
    """
    Remove method provenance from the expert-facing version.
    """
    expert_rows = []

    for row in internal_rows:
        expert_rows.append({
            "case_id": row["case_id"],
            "concept_id": row["concept_id"],
            "segment_excerpt": row["segment_excerpt"],
            "concept_label": row["concept_label"],
            "concept_uri": row["concept_uri"],
            "correctness": row["correctness"],
            "specificity": row["specificity"],
            "missing_concept_comment": row["missing_concept_comment"],
            "general_comment": row["general_comment"]
        })

    return expert_rows


def main() -> None:
    """
    Create internal and expert-facing evaluation tables.
    """
    print("=" * 100)
    print("CREATING EXPERT EVALUATION TABLES")
    print("=" * 100)

    print(f"Evaluation segments: {EVALUATION_SEGMENTS_JSON}")
    print(f"Baseline outputs: {BASELINE_DIR}")
    print(f"Refined outputs: {REFINED_DIR}")
    print(f"KG-RAG outputs: {KG_RAG_DIR}")
    print(f"Internal output: {INTERNAL_OUTPUT_CSV}")
    print(f"Expert-facing output: {EXPERT_OUTPUT_CSV}")
    print()

    segment_map = load_evaluation_segments()

    internal_rows = []

    for segment_id in EXPECTED_SEGMENTS:
        if segment_id not in segment_map:
            raise KeyError(f"Segment ID not found in evaluation segments: {segment_id}")

        rows = build_rows_for_segment(segment_id, segment_map[segment_id])
        internal_rows.extend(rows)

        print(f"- {segment_id} | concepts for expert review: {len(rows)}")

    expert_rows = create_expert_facing_rows(internal_rows)

    internal_fieldnames = [
        "case_id",
        "concept_id",
        "segment_id",
        "pilot_role",
        "segment_excerpt",
        "concept_label",
        "concept_uri",
        "selected_by_baseline",
        "selected_by_refined",
        "selected_by_kg_rag",
        "baseline_score",
        "refined_score",
        "kg_rag_score",
        "correctness",
        "specificity",
        "missing_concept_comment",
        "general_comment"
    ]

    expert_fieldnames = [
        "case_id",
        "concept_id",
        "segment_excerpt",
        "concept_label",
        "concept_uri",
        "correctness",
        "specificity",
        "missing_concept_comment",
        "general_comment"
    ]

    save_csv(INTERNAL_OUTPUT_CSV, internal_rows, internal_fieldnames)
    save_csv(EXPERT_OUTPUT_CSV, expert_rows, expert_fieldnames)

    print()
    print("=" * 100)
    print("EXPERT EVALUATION TABLES COMPLETE")
    print("=" * 100)
    print(f"Internal rows written: {len(internal_rows)}")
    print(f"Expert-facing rows written: {len(expert_rows)}")
    print(f"Saved internal table to: {INTERNAL_OUTPUT_CSV}")
    print(f"Saved expert-facing table to: {EXPERT_OUTPUT_CSV}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()