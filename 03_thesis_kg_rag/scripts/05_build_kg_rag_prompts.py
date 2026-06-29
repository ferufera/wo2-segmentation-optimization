"""
05_build_kg_rag_prompts.py

Step 5 of the KG-RAG thesis pipeline.

This script builds LLM concept selection prompts from retrieved candidate
concepts.

Input:
    Prefer:
        results/candidate_outputs/evaluation_candidates.json

    Fallback for prototype testing:
        results/candidate_outputs/test_retrieval_candidates.json

Output:
    results/llm_prompts/kg_rag/

Why I do this:
    Candidate retrieval and LLM prompting are separate steps. This script takes
    the retrieved WO2 Thesaurus candidates and creates prompt files that can be
    manually pasted into the same GPT model for concept selection.

Important:
    This script must not include validation comments, consensus status, removed
    concepts, or missing-concept comments in the prompt. Those fields are part of
    the evaluation data and should not be shown to the model.
"""

import json
from pathlib import Path

from kg_rag_prompts import _build_kg_rag_concept_selection_prompt


BASE_DIR = Path(__file__).resolve().parents[1]

CANDIDATE_OUTPUT_DIR = BASE_DIR / "results" / "candidate_outputs"

EVALUATION_CANDIDATES_JSON = CANDIDATE_OUTPUT_DIR / "evaluation_candidates.json"
TEST_CANDIDATES_JSON = CANDIDATE_OUTPUT_DIR / "test_retrieval_candidates.json"

OUTPUT_DIR = BASE_DIR / "results" / "llm_prompts" / "kg_rag"


def choose_candidate_file() -> Path:
    """
    Choose which candidate file to use.

    I prefer the real evaluation candidate file. If that does not exist yet, I
    fall back to the prototype test candidate file.
    """
    if EVALUATION_CANDIDATES_JSON.exists():
        return EVALUATION_CANDIDATES_JSON

    if TEST_CANDIDATES_JSON.exists():
        return TEST_CANDIDATES_JSON

    raise FileNotFoundError(
        "No candidate file found. Expected one of:\n"
        f"- {EVALUATION_CANDIDATES_JSON}\n"
        f"- {TEST_CANDIDATES_JSON}"
    )


def load_candidate_results(candidate_file: Path) -> list[dict]:
    """
    Load candidate retrieval results.
    """
    with open(candidate_file, "r", encoding="utf-8") as file:
        return json.load(file)


def build_prompt_for_result(result: dict) -> str:
    """
    Build one KG-RAG prompt from one candidate retrieval result.

    Only segment text and retrieved candidate concepts are passed to the prompt
    builder. Validation information is intentionally excluded.
    """
    segment_id = result["segment_id"]
    segment_text = result.get("text", "")
    candidates = result.get("candidates", [])

    return _build_kg_rag_concept_selection_prompt(
        segment_id=segment_id,
        segment_text=segment_text,
        candidates=candidates
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
    Save one prompt to a text file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_filename(segment_id)}_kg_rag_prompt.txt"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(prompt_text)

    return output_path


def main() -> None:
    """
    Build KG-RAG prompt files for all candidate retrieval results.
    """
    candidate_file = choose_candidate_file()

    print("=" * 100)
    print("BUILDING KG-RAG PROMPTS")
    print("=" * 100)
    print(f"Using candidate file: {candidate_file}")

    candidate_results = load_candidate_results(candidate_file)

    print(f"Loaded candidate results: {len(candidate_results)}")
    print(f"Saving prompts to: {OUTPUT_DIR}")
    print()

    total_candidates = 0

    for result in candidate_results:
        segment_id = result["segment_id"]
        candidates = result.get("candidates", [])
        total_candidates += len(candidates)

        prompt_text = build_prompt_for_result(result)
        output_path = save_prompt(segment_id, prompt_text)

        print(
            f"Saved prompt: {output_path.name} "
            f"| candidates included: {len(candidates)}"
        )

    print()
    print("=" * 100)
    print("KG-RAG PROMPT SUMMARY")
    print("=" * 100)
    print(f"Segments processed: {len(candidate_results)}")
    print(f"Total candidates included across prompts: {total_candidates}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()