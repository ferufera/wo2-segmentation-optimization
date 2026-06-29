"""
11_summarize_baseline_outputs.py

Step 11 of the KG-RAG thesis pipeline.

This script creates a compact summary table from the cleaned baseline prompting
LLM outputs.

Input:
    results/llm_outputs/baseline_cleaned/

Output:
    results/validation_reports/baseline_result_summary.csv

Why I do this:
    After manually running the baseline prompts, I need a compact overview of
    the selected concepts before comparing the baseline condition with the
    refined and KG-RAG conditions.

The baseline outputs have this JSON format:

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

INPUT_DIR = BASE_DIR / "results" / "llm_outputs" / "baseline_cleaned"
OUTPUT_DIR = BASE_DIR / "results" / "validation_reports"
OUTPUT_CSV = OUTPUT_DIR / "baseline_result_summary.csv"


PILOT_METADATA = {
    "02%20stiso_20091008_Huffener_Lotty_1.nl_8": {
        "pilot_role": "organisation_work_conflict_case",
        "important_success": "Selected Philips, Dwangarbeid, and Gevangenen.",
        "debatable_selections": "Dwangarbeid and Gevangenen may require expert judgement because KG-RAG selected only Philips.",
        "comparison_to_refined": "Refined selected the same three concepts, with slightly different scores.",
        "comparison_to_kg_rag": "KG-RAG selected only Philips, making it more conservative for this segment.",
        "notes": "Baseline and refined are very similar for this case."
    },
    "01_JKKV_2003_LOTTY_HUFFENER-Veffer-h264.nl_1": {
        "pilot_role": "missing_camp_concepts_case",
        "important_success": "Selected Vught, Auschwitz, and Kamp Vught.",
        "debatable_selections": "Selected both Vught and Kamp Vught, which is redundant. Also selected Transporten and Gevangenen.",
        "comparison_to_refined": "Refined selected only Kamp Vught and Auschwitz, reducing redundancy and generic concepts.",
        "comparison_to_kg_rag": "KG-RAG selected Reichenbach and Birkenau, which were missing from the baseline candidate list.",
        "notes": "Shows refined prompting can improve filtering, while KG-RAG can recover missing specific concepts."
    },
    "04_JKKV_2003_ANNIE_SULZBACH-h264.nl_3": {
        "pilot_role": "missing_event_concept_case",
        "important_success": "Selected family, housing, moving, and Amsterdam-related concepts.",
        "debatable_selections": "Did not select Kristallnacht because it was not available in the original candidate list.",
        "comparison_to_refined": "Baseline and refined produced almost the same selected concepts.",
        "comparison_to_kg_rag": "KG-RAG selected Kristallnacht because retrieval added the missing event concept.",
        "notes": "Shows prompt-only methods cannot recover missing event concepts absent from the candidate list."
    },
    "08%20stiso_20091104_Wurms_Rob_1.nl_10": {
        "pilot_role": "accepted_control_case",
        "important_success": "Selected Auschwitz, Sobibor, and Barakken.",
        "debatable_selections": "Selected Oorlogsgetroffenen and Monnickendam, which may be broader or less central.",
        "comparison_to_refined": "Refined removed Oorlogsgetroffenen but kept Monnickendam.",
        "comparison_to_kg_rag": "KG-RAG selected more specific concepts such as Auschwitz-Birkenau, Gas chambers, Krakau, and Oswiecim.",
        "notes": "Shows refined prompting may reduce generic tagging, while KG-RAG expands specific candidate coverage."
    },
    "22%20stiso_20110501_Zeehandelaar_Geertruida_1.nl_4": {
        "pilot_role": "specific_place_disambiguation_case",
        "important_success": "Selected Sobibor, Westerbork, Auschwitz, and Pearl Harbor.",
        "debatable_selections": "Selected Bergen instead of Bergen-Belsen.",
        "comparison_to_refined": "Baseline and refined selected the same concept list.",
        "comparison_to_kg_rag": "KG-RAG selected Bergen-Belsen and rejected Bergen.",
        "notes": "Strong case showing KG-RAG improves place/camp disambiguation when a more specific concept is retrieved."
    }
}


def load_json_file(path: Path):
    """
    Load one cleaned baseline output JSON file.
    """
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def infer_segment_id_from_filename(path: Path) -> str:
    """
    Infer the segment ID from the baseline output filename.

    Expected filename pattern:
        <segment_id>_baseline_output_cleaned.json
    """
    name = path.name

    if not name.endswith("_baseline_output_cleaned.json"):
        raise ValueError(
            f"Unexpected filename format: {path.name}\n"
            "Expected filename ending with: _baseline_output_cleaned.json"
        )

    segment_id = name.replace("_baseline_output_cleaned.json", "")

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
    Extract selected concept names from one baseline output.
    """
    return [
        item.get("concept", "")
        for item in output
        if item.get("concept", "")
    ]


def extract_scores(output: list[dict]) -> list[float]:
    """
    Extract confidence scores from one baseline output.
    """
    scores = []

    for item in output:
        score = item.get("score")

        if isinstance(score, (int, float)):
            scores.append(float(score))

    return scores


def build_summary_row(output: list[dict], source_file: Path) -> dict:
    """
    Build one row for the baseline result summary table.
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
        "comparison_to_refined": metadata.get("comparison_to_refined", ""),
        "comparison_to_kg_rag": metadata.get("comparison_to_kg_rag", ""),
        "notes": metadata.get("notes", "")
    }


def collect_cleaned_outputs() -> list[Path]:
    """
    Collect all cleaned baseline output JSON files.
    """
    if not INPUT_DIR.exists():
        raise FileNotFoundError(
            f"Input directory does not exist:\n{INPUT_DIR}\n\n"
            "Expected cleaned baseline outputs in this folder."
        )

    files = sorted(INPUT_DIR.glob("*_baseline_output_cleaned.json"))

    if not files:
        raise FileNotFoundError(
            f"No cleaned baseline output files found in:\n{INPUT_DIR}\n\n"
            "Expected files ending with: _baseline_output_cleaned.json"
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
        "comparison_to_refined",
        "comparison_to_kg_rag",
        "notes"
    ]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """
    Create a baseline result summary table from cleaned output files.
    """
    print("=" * 100)
    print("CREATING BASELINE RESULT SUMMARY")
    print("=" * 100)

    print(f"Input directory: {INPUT_DIR}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print()

    files = collect_cleaned_outputs()
    print(f"Found cleaned baseline output files: {len(files)}")

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
    print("BASELINE SUMMARY COMPLETE")
    print("=" * 100)
    print(f"Rows written: {len(rows)}")
    print(f"Saved to: {OUTPUT_CSV}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()