"""
09_summarize_refined_outputs.py

Step 9 of the KG-RAG thesis pipeline.

This script creates a compact summary table from the cleaned refined prompting
LLM outputs.

Input:
    results/llm_outputs/refined_cleaned/

Output:
    results/validation_reports/refined_result_summary.csv

Why I do this:
    After manually running the refined prompts, I need a compact overview of
    the selected concepts before comparing the refined condition with the
    KG-RAG condition and preparing the expert evaluation.

The refined outputs have a simpler JSON format than the KG-RAG outputs:

[
  {
    "concept": "Concept name",
    "score": 0.95
  }
]
"""

import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = BASE_DIR / "results" / "llm_outputs" / "refined_cleaned"
OUTPUT_DIR = BASE_DIR / "results" / "validation_reports"
OUTPUT_CSV = OUTPUT_DIR / "refined_result_summary.csv"


PILOT_METADATA = {
    "02%20stiso_20091008_Huffener_Lotty_1.nl_8": {
        "pilot_role": "organisation_work_conflict_case",
        "important_success": "Selected Philips, Dwangarbeid, and Gevangenen.",
        "debatable_selections": "Dwangarbeid and Gevangenen are more inclusive than the KG-RAG output and may require expert judgement.",
        "comparison_to_kg_rag": "KG-RAG selected only Philips. Refined prompting was more inclusive for this segment.",
        "notes": "Useful case showing refined prompting may keep broader/contextual concepts that KG-RAG rejected."
    },
    "01_JKKV_2003_LOTTY_HUFFENER-Veffer-h264.nl_1": {
        "pilot_role": "missing_camp_concepts_case",
        "important_success": "Selected Kamp Vught and Auschwitz.",
        "debatable_selections": "Did not recover Reichenbach or Birkenau.",
        "comparison_to_kg_rag": "KG-RAG selected Reichenbach and Birkenau because these were added by retrieval. Refined prompting could not select them because they were absent from the original candidate list.",
        "notes": "Shows that prompt refinement cannot recover concepts missing from the candidate list."
    },
    "04_JKKV_2003_ANNIE_SULZBACH-h264.nl_3": {
        "pilot_role": "missing_event_concept_case",
        "important_success": "Selected family, housing, and location-related concepts.",
        "debatable_selections": "Did not recover Kristallnacht.",
        "comparison_to_kg_rag": "KG-RAG selected Kristallnacht, while refined prompting did not because it was absent from the original candidate list.",
        "notes": "Another example showing that KG-RAG can recover missing specific event concepts when retrieval adds them."
    },
    "08%20stiso_20091104_Wurms_Rob_1.nl_10": {
        "pilot_role": "accepted_control_case",
        "important_success": "Selected Auschwitz, Sobibor, and Barakken.",
        "debatable_selections": "Monnickendam is textually mentioned but may be less central.",
        "comparison_to_kg_rag": "KG-RAG selected more specific Auschwitz-related concepts, including Auschwitz-Birkenau, Gas chambers, Krakau, and Oswiecim.",
        "notes": "Refined prompting selected several core concepts but remained limited by the original candidate list."
    },
    "22%20stiso_20110501_Zeehandelaar_Geertruida_1.nl_4": {
        "pilot_role": "specific_place_disambiguation_case",
        "important_success": "Selected Sobibor, Westerbork, Auschwitz, and Pearl Harbor.",
        "debatable_selections": "Selected Bergen instead of Bergen-Belsen.",
        "comparison_to_kg_rag": "KG-RAG selected Bergen-Belsen and rejected Bergen, showing better place/camp disambiguation.",
        "notes": "Strong comparison case showing the limitation of refined prompting when the more specific concept is missing from the original candidate list."
    }
}


def load_json_file(path: Path):
    """
    Load one cleaned refined output JSON file.
    """
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def infer_segment_id_from_filename(path: Path) -> str:
    """
    Infer the segment ID from the refined output filename.

    Expected filename pattern:
        <segment_id>_refined_output_cleaned.json
    """
    name = path.name

    if not name.endswith("_refined_output_cleaned.json"):
        raise ValueError(
            f"Unexpected filename format: {path.name}\n"
            "Expected filename ending with: _refined_output_cleaned.json"
        )

    segment_id = name.replace("_refined_output_cleaned.json", "")

    # Reverse the filename-safe replacement used earlier for %20 only where needed.
    # Some segment IDs originally contain %20, while filenames use underscores.
    # We map known safe filenames back to their original segment IDs using metadata.
    for known_segment_id in PILOT_METADATA:
        safe_known = (
            known_segment_id
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
            .replace("%20", "_")
            .replace(" ", "_")
        )
        if segment_id == safe_known:
            return known_segment_id

    return segment_id


def extract_concepts(output: list[dict]) -> list[str]:
    """
    Extract selected concept names from one refined output.
    """
    return [
        item.get("concept", "")
        for item in output
        if item.get("concept", "")
    ]


def extract_scores(output: list[dict]) -> list[float]:
    """
    Extract confidence scores from one refined output.
    """
    scores = []

    for item in output:
        score = item.get("score")

        if isinstance(score, (int, float)):
            scores.append(float(score))

    return scores


def build_summary_row(output: list[dict], source_file: Path) -> dict:
    """
    Build one row for the refined result summary table.
    """
    segment_id = infer_segment_id_from_filename(source_file)

    concepts = extract_concepts(output)
    scores = extract_scores(output)

    metadata = PILOT_METADATA.get(segment_id, {})

    average_score = round(sum(scores) / len(scores), 3) if scores else ""

    return {
        "segment_id": segment_id,
        "source_file": source_file.name,
        "pilot_role": metadata.get("pilot_role", "UNKNOWN"),
        "selected_concepts": "; ".join(concepts),
        "selected_count": len(concepts),
        "scores": "; ".join(str(score) for score in scores),
        "average_score": average_score,
        "important_success": metadata.get("important_success", ""),
        "debatable_selections": metadata.get("debatable_selections", ""),
        "comparison_to_kg_rag": metadata.get("comparison_to_kg_rag", ""),
        "notes": metadata.get("notes", "")
    }


def collect_cleaned_outputs() -> list[Path]:
    """
    Collect all cleaned refined output JSON files.
    """
    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"Input directory does not exist:\n{INPUT_DIR}\n\n"
            "Expected cleaned refined outputs in this folder."
        )

    files = sorted(INPUT_DIR.glob("*_refined_output_cleaned.json"))

    if not files:
        raise FileNotFoundError(
            f"No cleaned refined output files found in:\n{INPUT_DIR}\n\n"
            "Expected files ending with: _refined_output_cleaned.json"
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
        "scores",
        "average_score",
        "important_success",
        "debatable_selections",
        "comparison_to_kg_rag",
        "notes"
    ]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """
    Create a refined result summary table from cleaned output files.
    """
    print("=" * 100)
    print("CREATING REFINED RESULT SUMMARY")
    print("=" * 100)

    print(f"Input directory: {INPUT_DIR}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print()

    files = collect_cleaned_outputs()
    print(f"Found cleaned refined output files: {len(files)}")

    rows = []

    for path in files:
        output = load_json_file(path)

        if not isinstance(output, list):
            raise ValueError(
                f"Expected JSON list in {path.name}, but found {type(output)}"
            )

        row = build_summary_row(output, path)
        rows.append(row)

        print(
            f"- {row['segment_id']} | "
            f"selected: {row['selected_count']} | "
            f"average score: {row['average_score']}"
        )

    save_summary_csv(rows)

    print()
    print("=" * 100)
    print("REFINED SUMMARY COMPLETE")
    print("=" * 100)
    print(f"Rows written: {len(rows)}")
    print(f"Saved to: {OUTPUT_CSV}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()