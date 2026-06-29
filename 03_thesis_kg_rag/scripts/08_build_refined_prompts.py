"""
08_build_refined_prompts.py

Step 8 of the KG-RAG thesis pipeline.

This script builds refined prompting condition files for the five thesis pilot
segments.

Input:
    data/evaluation_segments.json

Output:
    results/llm_prompts/refined/

Why I do this:
    The thesis compares three concept-linking conditions:
    1. baseline prompting
    2. previously developed refined prompting
    3. KG-RAG prompting

    This script creates the prompts for condition 2: refined prompting.

    The refined prompt uses the original WO2Net matched concepts as the
    candidate concept list. This makes it different from the KG-RAG condition,
    where the candidates come from the WO2 Thesaurus retrieval step.
"""

import json
from pathlib import Path

from refined_prompts import _build_topdown_matching_prompt


BASE_DIR = Path(__file__).resolve().parents[1]

EVALUATION_SEGMENTS_JSON = BASE_DIR / "data" / "evaluation_segments.json"

OUTPUT_DIR = BASE_DIR / "results" / "llm_prompts" / "refined"


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

    These are used as the concept list for the refined prompting condition.
    """
    concepts = segment.get("original_matched_concepts", [])

    labels = []

    for concept in concepts:
        name = concept.get("name", "").strip()

        if name and name not in labels:
            labels.append(name)

    return labels


def build_refined_prompt_for_segment(segment: dict) -> str:
    """
    Build one refined concept matching prompt.
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
    Save one refined prompt to a text file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_filename(segment_id)}_refined_prompt.txt"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(prompt_text)

    return output_path


def main() -> None:
    """
    Build refined prompt files for all five evaluation segments.
    """
    print("=" * 100)
    print("BUILDING REFINED PROMPTS")
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

        prompt_text = build_refined_prompt_for_segment(segment)
        output_path = save_prompt(segment_id, prompt_text)

        print(
            f"Saved prompt: {output_path.name} "
            f"| original concepts included: {len(concept_labels)}"
        )

    print()
    print("=" * 100)
    print("REFINED PROMPT SUMMARY")
    print("=" * 100)
    print(f"Segments processed: {len(segments)}")
    print(f"Total original concepts included across prompts: {total_concepts}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()