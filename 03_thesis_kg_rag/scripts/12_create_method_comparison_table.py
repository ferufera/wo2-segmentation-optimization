"""
12_create_method_comparison_table.py

Step 12 of the KG-RAG thesis pipeline.

This script creates a combined comparison table across the three concept-linking
conditions used in the thesis pilot:

1. Baseline prompting
2. Refined prompting
3. KG-RAG prompting

Inputs:
    results/llm_outputs/baseline_cleaned/
    results/llm_outputs/refined_cleaned/
    results/llm_outputs/kg_rag_cleaned/

Output:
    results/validation_reports/method_comparison_table.csv

Why I do this:
    The separate summary tables show the results of each method individually.
    This combined table makes it possible to compare the three methods for each
    pilot segment side by side.

    This is useful before preparing the expert evaluation because it shows which
    concepts should be included in the combined concept lists shown to historians.
"""

import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

BASELINE_DIR = BASE_DIR / "results" / "llm_outputs" / "baseline_cleaned"
REFINED_DIR = BASE_DIR / "results" / "llm_outputs" / "refined_cleaned"
KG_RAG_DIR = BASE_DIR / "results" / "llm_outputs" / "kg_rag_cleaned"

OUTPUT_DIR = BASE_DIR / "results" / "validation_reports"
OUTPUT_CSV = OUTPUT_DIR / "method_comparison_table.csv"


PILOT_METADATA = {
    "02%20stiso_20091008_Huffener_Lotty_1.nl_8": {
        "pilot_role": "organisation_work_conflict_case",
        "key_comparison": "Baseline and refined both selected Philips, Dwangarbeid, and Gevangenen. KG-RAG selected only Philips, making it more conservative for this segment.",
        "main_observation": "KG-RAG may reject contextual labour/prisoner concepts when the segment does not explicitly state coercion."
    },
    "01_JKKV_2003_LOTTY_HUFFENER-Veffer-h264.nl_1": {
        "pilot_role": "missing_camp_concepts_case",
        "key_comparison": "Baseline selected both Vught and Kamp Vught plus broader concepts. Refined selected Kamp Vught and Auschwitz. KG-RAG additionally selected Reichenbach and Birkenau.",
        "main_observation": "Refined prompting improved filtering among existing candidates, while KG-RAG recovered missing specific camp/place concepts."
    },
    "04_JKKV_2003_ANNIE_SULZBACH-h264.nl_3": {
        "pilot_role": "missing_event_concept_case",
        "key_comparison": "Baseline and refined selected family/housing concepts but not Kristallnacht. KG-RAG selected Kristallnacht.",
        "main_observation": "KG-RAG recovered a missing specific event concept that was absent from the original candidate list."
    },
    "08%20stiso_20091104_Wurms_Rob_1.nl_10": {
        "pilot_role": "accepted_control_case",
        "key_comparison": "Baseline and refined selected core concepts such as Auschwitz, Sobibor, and Barakken. KG-RAG selected additional specific concepts such as Auschwitz-Birkenau, Gas chambers, Krakau, and Oswiecim.",
        "main_observation": "KG-RAG expanded the candidate set and selected more specific Auschwitz-related concepts, but also selected some potentially peripheral concepts."
    },
    "22%20stiso_20110501_Zeehandelaar_Geertruida_1.nl_4": {
        "pilot_role": "specific_place_disambiguation_case",
        "key_comparison": "Baseline and refined selected Bergen. KG-RAG selected Bergen-Belsen and rejected Bergen.",
        "main_observation": "KG-RAG improved place/camp disambiguation by retrieving the more specific camp concept."
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


def extract_prompt_output_concepts(output: list[dict]) -> list[str]:
    """
    Extract concept names from baseline or refined output format.

    Expected format:
    [
      {"concept": "Auschwitz", "score": 0.99}
    ]
    """
    concepts = []

    for item in output:
        concept = item.get("concept", "").strip()

        if concept and concept not in concepts:
            concepts.append(concept)

    return concepts


def extract_kg_rag_concepts(output: dict) -> list[str]:
    """
    Extract selected concept labels from KG-RAG output format.

    Expected format:
    {
      "selected_concepts": [
        {"label": "Auschwitz", ...}
      ]
    }
    """
    concepts = []

    for item in output.get("selected_concepts", []):
        label = item.get("label", "").strip()

        if label and label not in concepts:
            concepts.append(label)

    return concepts


def get_baseline_output_path(segment_id: str) -> Path:
    """
    Get cleaned baseline output path for a segment.
    """
    safe_id = safe_filename(segment_id)
    return BASELINE_DIR / f"{safe_id}_baseline_output_cleaned.json"


def get_refined_output_path(segment_id: str) -> Path:
    """
    Get cleaned refined output path for a segment.
    """
    safe_id = safe_filename(segment_id)
    return REFINED_DIR / f"{safe_id}_refined_output_cleaned.json"


def get_kg_rag_output_path(segment_id: str) -> Path:
    """
    Get cleaned KG-RAG output path for a segment.
    """
    safe_id = safe_filename(segment_id)
    return KG_RAG_DIR / f"{safe_id}_kg_rag_output_cleaned.json"


def build_comparison_row(segment_id: str) -> dict:
    """
    Build one row comparing baseline, refined, and KG-RAG outputs.
    """
    baseline_output = load_json(get_baseline_output_path(segment_id))
    refined_output = load_json(get_refined_output_path(segment_id))
    kg_rag_output = load_json(get_kg_rag_output_path(segment_id))

    baseline_concepts = extract_prompt_output_concepts(baseline_output)
    refined_concepts = extract_prompt_output_concepts(refined_output)
    kg_rag_concepts = extract_kg_rag_concepts(kg_rag_output)

    metadata = PILOT_METADATA[segment_id]

    return {
        "segment_id": segment_id,
        "pilot_role": metadata["pilot_role"],
        "baseline_concepts": "; ".join(baseline_concepts),
        "baseline_count": len(baseline_concepts),
        "refined_concepts": "; ".join(refined_concepts),
        "refined_count": len(refined_concepts),
        "kg_rag_concepts": "; ".join(kg_rag_concepts),
        "kg_rag_count": len(kg_rag_concepts),
        "key_comparison": metadata["key_comparison"],
        "main_observation": metadata["main_observation"]
    }


def save_comparison_csv(rows: list[dict]) -> None:
    """
    Save comparison rows to CSV.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "segment_id",
        "pilot_role",
        "baseline_concepts",
        "baseline_count",
        "refined_concepts",
        "refined_count",
        "kg_rag_concepts",
        "kg_rag_count",
        "key_comparison",
        "main_observation"
    ]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """
    Create the combined method comparison table.
    """
    print("=" * 100)
    print("CREATING METHOD COMPARISON TABLE")
    print("=" * 100)

    print(f"Baseline input folder: {BASELINE_DIR}")
    print(f"Refined input folder: {REFINED_DIR}")
    print(f"KG-RAG input folder: {KG_RAG_DIR}")
    print(f"Output CSV: {OUTPUT_CSV}")
    print()

    rows = []

    for segment_id in EXPECTED_SEGMENTS:
        row = build_comparison_row(segment_id)
        rows.append(row)

        print(
            f"- {segment_id} | "
            f"baseline: {row['baseline_count']} | "
            f"refined: {row['refined_count']} | "
            f"KG-RAG: {row['kg_rag_count']}"
        )

    save_comparison_csv(rows)

    print()
    print("=" * 100)
    print("METHOD COMPARISON TABLE COMPLETE")
    print("=" * 100)
    print(f"Rows written: {len(rows)}")
    print(f"Saved to: {OUTPUT_CSV}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()