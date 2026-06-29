"""
04_run_candidate_retrieval.py

Step 4 of the KG-RAG thesis pipeline.

This script runs WO2 Thesaurus candidate retrieval on the selected real pilot
segments.

Input:
    data/thesaurus_concepts.csv
    data/evaluation_segments.json

Output:
    results/candidate_outputs/evaluation_candidates.json
    results/candidate_outputs/evaluation_candidates.csv

Why I do this:
    In the previous step, I selected five real WO2Net pilot segments from the
    evaluation shortlist. This script now retrieves candidate concepts from the
    parsed WO2 Thesaurus for each of those real segments.

Pipeline position:
    selected real WO2Net segments
        -> candidate retrieval from WO2 Thesaurus
        -> saved candidate list
        -> KG-RAG prompt generation in the next step

Important:
    This script does not call the LLM. It only retrieves candidate concepts.
"""

import csv
import json
from pathlib import Path

from retrieve_candidates import load_thesaurus, retrieve_candidates


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

BASE_DIR = Path(__file__).resolve().parents[1]

THESAURUS_CSV = BASE_DIR / "data" / "thesaurus_concepts.csv"
EVALUATION_SEGMENTS_JSON = BASE_DIR / "data" / "evaluation_segments.json"

OUTPUT_DIR = BASE_DIR / "results" / "candidate_outputs"
OUTPUT_JSON = OUTPUT_DIR / "evaluation_candidates.json"
OUTPUT_CSV = OUTPUT_DIR / "evaluation_candidates.csv"


# =============================================================================
# SETTINGS
# =============================================================================

TOP_K_CANDIDATES = 40


# =============================================================================
# DATA LOADING
# =============================================================================

def load_evaluation_segments() -> list[dict]:
    """
    Load the selected real pilot segments.

    These segments were selected from the real WO2Net enriched segments and
    crowd validation data. They are not artificial test examples.
    """
    if not EVALUATION_SEGMENTS_JSON.exists():
        raise FileNotFoundError(
            f"Evaluation segments file not found: {EVALUATION_SEGMENTS_JSON}\n"
            "Create data/evaluation_segments.json first."
        )

    with open(EVALUATION_SEGMENTS_JSON, "r", encoding="utf-8") as file:
        return json.load(file)


# =============================================================================
# RETRIEVAL
# =============================================================================

def run_retrieval_for_segment(
    segment: dict,
    concepts_by_id: dict,
    searchable_labels: list[dict]
) -> dict:
    """
    Run candidate retrieval for one selected pilot segment.

    The output keeps the segment metadata together with the retrieved candidates.
    This makes later inspection easier because I can see:
        - what the segment text was
        - what the original pipeline matched
        - what crowd validators said
        - what KG retrieval returned
    """
    segment_id = segment["segment_id"]
    segment_text = segment["text"]

    candidates = retrieve_candidates(
    segment_text=segment_text,
    concepts_by_id=concepts_by_id,
    searchable_labels=searchable_labels,
    top_k=TOP_K_CANDIDATES,
    original_matched_concepts=segment.get("original_matched_concepts", [])
)

    return {
        "segment_id": segment_id,
        "segment_title": segment.get("segment_title", ""),
        "interviewee_name": segment.get("interviewee_name", ""),
        "video_name": segment.get("video_name", ""),
        "start": segment.get("start"),
        "end": segment.get("end"),
        "duration": segment.get("duration"),
        "pilot_role": segment.get("pilot_role", ""),
        "text": segment_text,
        "original_matched_concepts": segment.get("original_matched_concepts", []),
        "validation_summary": segment.get("validation_summary", {}),
        "keyword_hits": segment.get("keyword_hits", []),
        "selection_reason": segment.get("selection_reason", []),
        "candidates": candidates,
    }


# =============================================================================
# OUTPUT
# =============================================================================

def save_json(results: list[dict]) -> None:
    """
    Save full candidate retrieval results as JSON.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    print(f"Saved JSON candidate results to:")
    print(OUTPUT_JSON)


def save_csv(results: list[dict]) -> None:
    """
    Save candidate retrieval results as a flat CSV.

    This is useful for quickly checking whether the retrieval step returned
    reasonable candidate concepts for each selected segment.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "segment_id",
        "pilot_role",
        "segment_title",
        "consensus_status",
        "rank",
        "candidate_label",
        "candidate_uri",
        "candidate_types",
        "candidate_schemes",
        "retrieval_score",
        "candidate_source",
        "retrieval_reason",
    ]

    rows = []

    for result in results:
        segment_id = result["segment_id"]
        pilot_role = result.get("pilot_role", "")
        segment_title = result.get("segment_title", "")
        consensus_status = result.get("validation_summary", {}).get("consensus_status", "")

        for rank, candidate in enumerate(result.get("candidates", []), start=1):
            rows.append({
                "segment_id": segment_id,
                "pilot_role": pilot_role,
                "segment_title": segment_title,
                "consensus_status": consensus_status,
                "rank": rank,
                "candidate_label": candidate.get("label", ""),
                "candidate_uri": candidate.get("uri", ""),
                "candidate_types": " | ".join(candidate.get("types", [])),
                "candidate_schemes": " | ".join(candidate.get("schemes", [])),
                "retrieval_score": candidate.get("retrieval_score", ""),
                "candidate_source": candidate.get("candidate_source", ""),
                "retrieval_reason": candidate.get("retrieval_reason", ""),
            })

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved CSV candidate results to:")
    print(OUTPUT_CSV)


def print_segment_summary(result: dict) -> None:
    """
    Print a compact summary for one segment.
    """
    print("\n" + "=" * 100)
    print(f"SEGMENT: {result['segment_id']}")
    print(f"Role: {result.get('pilot_role', '')}")
    print(f"Title: {result.get('segment_title', '')}")
    print(f"Consensus: {result.get('validation_summary', {}).get('consensus_status', '')}")
    print(f"Keyword hits from shortlist: {', '.join(result.get('keyword_hits', []))}")

    comments = result.get("validation_summary", {}).get("comments", [])

    if comments:
        print("Validation comments:")
        for comment in comments[:3]:
            print(f"- {comment.replace(chr(10), ' | ')}")

    print("\nTop retrieved candidates:")

    for rank, candidate in enumerate(result.get("candidates", [])[:15], start=1):
        label = candidate.get("label", "")
        uri = candidate.get("uri", "")
        score = candidate.get("retrieval_score", "")
        source = candidate.get("candidate_source", "")
        reason = candidate.get("retrieval_reason", "")

        print(
            f"{rank:02d}. {label} | score={score} | "
            f"source={source} | reason={reason} | uri={uri}"
        )


def print_overall_summary(results: list[dict]) -> None:
    """
    Print a summary after retrieval is complete.
    """
    print("\n" + "=" * 100)
    print("EVALUATION CANDIDATE RETRIEVAL SUMMARY")
    print("=" * 100)

    print(f"Segments processed: {len(results)}")

    for result in results:
        print(
            f"- {result['segment_id']} | "
            f"{result.get('pilot_role', '')} | "
            f"{len(result.get('candidates', []))} candidates"
        )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """
    Run candidate retrieval on the selected real pilot segments.
    """
    print("Loading WO2 Thesaurus...")
    print(f"Thesaurus CSV: {THESAURUS_CSV}")

    concepts_by_id, searchable_labels = load_thesaurus(str(THESAURUS_CSV))

    print(f"Loaded concepts: {len(concepts_by_id)}")
    print(f"Loaded searchable labels: {len(searchable_labels)}")

    print("\nLoading selected evaluation segments...")
    print(f"Evaluation segments file: {EVALUATION_SEGMENTS_JSON}")

    evaluation_segments = load_evaluation_segments()

    print(f"Loaded evaluation segments: {len(evaluation_segments)}")

    results = []

    for segment in evaluation_segments:
        result = run_retrieval_for_segment(
            segment=segment,
            concepts_by_id=concepts_by_id,
            searchable_labels=searchable_labels
        )

        results.append(result)
        print_segment_summary(result)

    save_json(results)
    save_csv(results)
    print_overall_summary(results)

    print("\nDone. Candidate retrieval for real pilot segments is complete.")


if __name__ == "__main__":
    main()