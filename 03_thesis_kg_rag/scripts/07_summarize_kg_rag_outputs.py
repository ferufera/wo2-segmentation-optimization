"""
07_summarize_kg_rag_outputs.py

Step 7 of the KG-RAG thesis pipeline.

This script creates a compact summary table from the cleaned KG-RAG LLM outputs.

Input:
    results/llm_outputs/kg_rag_cleaned/

Output:
    results/validation_reports/kg_rag_result_summary.csv

Why I do this:
    After manually running the KG-RAG prompts and cleaning the outputs, I need
    a compact overview of the results before preparing the expert evaluation.
    This summary table helps inspect which concepts were selected, which pilot
    goals were met, and which selections remain debatable.
"""

import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = BASE_DIR / "results" / "llm_outputs" / "kg_rag_cleaned"
OUTPUT_DIR = BASE_DIR / "results" / "validation_reports"
OUTPUT_CSV = OUTPUT_DIR / "kg_rag_result_summary.csv"


# Manual metadata for the five pilot cases.
# This keeps the summary interpretable instead of only listing raw selected concepts.
PILOT_METADATA = {
    "02%20stiso_20091008_Huffener_Lotty_1.nl_8": {
        "pilot_role": "organisation_work_conflict_case",
        "important_success": "Selected Philips.",
        "debatable_selections": "Rejected Forced labour although it may be contextually relevant.",
        "notable_rejections": "Gedetineerden; Forced labour",
        "notes": "Shows conservative selection when coercive labour context is implicit."
    },
    "01_JKKV_2003_LOTTY_HUFFENER-Veffer-h264.nl_1": {
        "pilot_role": "missing_camp_concepts_case",
        "important_success": "Selected Reichenbach and Birkenau.",
        "debatable_selections": "Amsterdam is factually correct but less central.",
        "notable_rejections": "Auschwitz-Birkenau; Vught; Geboren; fixedDateEvent",
        "notes": "Shows recovery of missing camp/place concepts."
    },
    "04_JKKV_2003_ANNIE_SULZBACH-h264.nl_3": {
        "pilot_role": "missing_event_concept_case",
        "important_success": "Selected Kristallnacht.",
        "debatable_selections": "Several family, housing, and location concepts may be less central.",
        "notable_rejections": "Overval op het Huis van Bewaring; Kindertransport; Raubüberfall",
        "notes": "Shows recovery of a missing event concept, but also broadens the output."
    },
    "08%20stiso_20091104_Wurms_Rob_1.nl_10": {
        "pilot_role": "accepted_control_case",
        "important_success": "Selected core Auschwitz-related concepts and rejected many noisy candidates.",
        "debatable_selections": "Ondergedoken; Netherlands; Utrecht may be less central.",
        "notable_rejections": "De Grote Oorlog; false-positive organizations; intervalEvent; fixedDateEvent",
        "notes": "Shows KG-RAG can filter noisy candidate lists, but still selects some peripheral concepts."
    },
    "22%20stiso_20110501_Zeehandelaar_Geertruida_1.nl_4": {
        "pilot_role": "specific_place_disambiguation_case",
        "important_success": "Selected Bergen-Belsen and rejected Bergen.",
        "debatable_selections": "Contact Holland and Overleden may be debatable.",
        "notable_rejections": "Bergen; De Grote Oorlog; Aktion Reinhard; fixedDateEvent",
        "notes": "Shows successful place/camp disambiguation."
    }
}


def load_json_file(path: Path) -> dict:
    """
    Load one cleaned KG-RAG output JSON file.
    """
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_selected_labels(output: dict) -> list[str]:
    """
    Extract selected concept labels from one KG-RAG output.
    """
    return [
        concept.get("label", "")
        for concept in output.get("selected_concepts", [])
        if concept.get("label", "")
    ]


def get_rejected_labels(output: dict) -> list[str]:
    """
    Extract rejected concept labels from one KG-RAG output.
    """
    return [
        concept.get("label", "")
        for concept in output.get("rejected_candidates", [])
        if concept.get("label", "")
    ]


def get_missing_suggestions(output: dict) -> list[str]:
    """
    Extract missing candidate suggestions from one KG-RAG output.
    """
    return [
        suggestion.get("label_or_keyword", "")
        for suggestion in output.get("missing_candidate_suggestions", [])
        if suggestion.get("label_or_keyword", "")
    ]


def build_summary_row(output: dict, source_file: Path) -> dict:
    """
    Build one row for the KG-RAG result summary table.
    """
    segment_id = output.get("segment_id", "")
    selected_labels = get_selected_labels(output)
    rejected_labels = get_rejected_labels(output)
    missing_suggestions = get_missing_suggestions(output)

    metadata = PILOT_METADATA.get(segment_id, {})

    return {
        "segment_id": segment_id,
        "source_file": source_file.name,
        "pilot_role": metadata.get("pilot_role", "UNKNOWN"),
        "selected_concepts": "; ".join(selected_labels),
        "selected_count": len(selected_labels),
        "rejected_count": len(rejected_labels),
        "missing_candidate_suggestions": "; ".join(missing_suggestions),
        "important_success": metadata.get("important_success", ""),
        "debatable_selections": metadata.get("debatable_selections", ""),
        "notable_rejections": metadata.get("notable_rejections", ""),
        "notes": metadata.get("notes", "")
    }


def collect_cleaned_outputs() -> list[Path]:
    """
    Collect all cleaned KG-RAG output JSON files.
    """
    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"Input directory does not exist:\n{INPUT_DIR}\n\n"
            "Expected cleaned KG-RAG outputs in this folder."
        )

    files = sorted(INPUT_DIR.glob("*_kg_rag_output_cleaned.json"))

    if not files:
        raise FileNotFoundError(
            f"No cleaned KG-RAG output files found in:\n{INPUT_DIR}\n\n"
            "Expected files ending with: _kg_rag_output_cleaned.json"
        )

    return files


def save_summary_csv(rows: list[dict]) -> None:
    """
    Save summary rows to CSV.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "segment_id",
        "source_file",
        "pilot_role",
        "selected_concepts",
        "selected_count",
        "rejected_count",
        "missing_candidate_suggestions",
        "important_success",
        "debatable_selections",
        "notable_rejections",
        "notes"
    ]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """
    Create a KG-RAG result summary table from cleaned output files.
    """
    print("=" * 100)
    print("CREATING KG-RAG RESULT SUMMARY")
    print("=" * 100)

    print(f"Input directory: {INPUT_DIR}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print()

    files = collect_cleaned_outputs()
    print(f"Found cleaned KG-RAG output files: {len(files)}")

    rows = []

    for path in files:
        output = load_json_file(path)
        row = build_summary_row(output, path)
        rows.append(row)

        print(
            f"- {row['segment_id']} | "
            f"selected: {row['selected_count']} | "
            f"rejected: {row['rejected_count']}"
        )

    save_summary_csv(rows)

    print()
    print("=" * 100)
    print("SUMMARY COMPLETE")
    print("=" * 100)
    print(f"Rows written: {len(rows)}")
    print(f"Saved to: {OUTPUT_CSV}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()