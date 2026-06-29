"""
10_build_baseline_prompts.py

Step 10 of the KG-RAG thesis pipeline.

This script builds baseline prompting condition files for the five thesis pilot
segments.

Input:
    data/evaluation_segments.json

Output:
    results/llm_prompts/baseline/

Why I do this:
    The thesis compares three concept-linking conditions:
    1. baseline prompting
    2. previously developed refined prompting
    3. KG-RAG prompting

    This script creates the prompts for condition 1: baseline prompting.

    The baseline prompt uses the original WO2Net matched concepts as the
    candidate concept list and applies the original top-down prompt logic from
    the previous WO2Net optimization work.
"""

import json
from pathlib import Path

from baseline_prompts import _build_topdown_matching_prompt


BASE_DIR = Path(__file__).resolve().parents[1]

EVALUATION_SEGMENTS_JSON = BASE_DIR / "data" / "evaluation_segments.json"

OUTPUT_DIR = BASE_DIR / "results" / "llm_prompts" / "baseline"


def load_evaluation_segments() -> list[dict]:
    """
    Load the selected five evaluation segments.
    """
    if not EVALUATION_SEGMENTS_JSON.exists():
        raise FileNotFoundError(
            f"Evaluation segments file not found:\n{EVALUATION_SEGMENTS_JSON}"
        )

    with open(EVALUATION_SEGMENTS_JSON, "r", encoding="utf-8") as file:
        return json.load(file)


def extract_original_concept_labels(segment: dict) -> list[str]:
    """
    Extract original WO2Net matched concept names from one segment.

    These are used as the concept list for the baseline prompting condition.
    """
    concepts = segment.get("original_matched_concepts", [])

    labels = []

    for concept in concepts:
        name = concept.get("name", "").strip()

        if name and name not in labels:
            labels.append(name)

    return labels


def build_baseline_prompt_for_segment(segment: dict) -> str:
    """
    Build one baseline concept matching prompt.
    """
    segment_text = segment.get("text", "")
    concept_labels = extract_original_concept_labels(segment)

    return _build_topdown_matching_prompt(
        concept_labels=concept_labels,
        segment_text=segment_text
    )


def safe_filename(segment_id: str) -> str:
    """
    Make a safe filename from a segment ID.
    """
    return (
        segment_id
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("%20", "_")
        .replace(" ", "_")
    )


def save_prompt(segment_id: str, prompt_text: str) -> Path:
    """
    Save one baseline prompt to a text file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_filename(segment_id)}_baseline_prompt.txt"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(prompt_text)

    return output_path


def main() -> None:
    """
    Build baseline prompt files for all five evaluation segments.
    """
    print("=" * 100)
    print("BUILDING BASELINE PROMPTS")
    print("=" * 100)

    print(f"Input file: {EVALUATION_SEGMENTS_JSON}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    segments = load_evaluation_segments()

    print(f"Loaded evaluation segments: {len(segments)}")
    print()

    total_concepts = 0

    for segment in segments:
        segment_id = segment["segment_id"]
        concept_labels = extract_original_concept_labels(segment)
        total_concepts += len(concept_labels)

        prompt_text = build_baseline_prompt_for_segment(segment)
        output_path = save_prompt(segment_id, prompt_text)

        print(
            f"Saved prompt: {output_path.name} "
            f"| original concepts included: {len(concept_labels)}"
        )

    print()
    print("=" * 100)
    print("BASELINE PROMPT SUMMARY")
    print("=" * 100)
    print(f"Segments processed: {len(segments)}")
    print(f"Total original concepts included across prompts: {total_concepts}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()