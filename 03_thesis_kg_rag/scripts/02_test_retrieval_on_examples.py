"""
02_test_retrieval_on_examples.py

Step 2 of the KG-RAG thesis pipeline.

This script tests the candidate retrieval logic on a few small example segments.

Input:
    data/thesaurus_concepts.csv
    data/test_segments.json

Output:
    results/candidate_outputs/test_retrieval_candidates.json
    results/candidate_outputs/test_retrieval_candidates.csv

Why I do this:
    Before running retrieval on real WO2Net segments, I first test whether the
    retrieval logic behaves reasonably on small examples. These examples are not
    the final thesis evaluation sample. They are only used for debugging the
    KG-RAG prototype.
"""

import csv
import json
from pathlib import Path

from retrieve_candidates import load_thesaurus, retrieve_candidates


BASE_DIR = Path(__file__).resolve().parents[1]

THESAURUS_CSV = BASE_DIR / "data" / "thesaurus_concepts.csv"
TEST_SEGMENTS_JSON = BASE_DIR / "data" / "test_segments.json"

OUTPUT_DIR = BASE_DIR / "results" / "candidate_outputs"
OUTPUT_JSON = OUTPUT_DIR / "test_retrieval_candidates.json"
OUTPUT_CSV = OUTPUT_DIR / "test_retrieval_candidates.csv"


DEFAULT_TEST_SEGMENTS = [
    {
        "segment_id": "rotterdam_test_01",
        "text": "Toen brak de oorlog uit, in mei 1940. We stonden met mijn vader en moeder en zagen Rotterdam in brand staan. Dat beeld is me altijd bijgebleven.",
        "expected_terms": [
            "Rotterdam",
            "Meidagen 1940",
            "Duitse inval in Nederland",
            "Duitse inval in Zuid-Holland"
        ]
    },
    {
        "segment_id": "kristallnacht_test_01",
        "text": "Hij vertelde over Kristallnacht en hoe de situatie voor Joodse gezinnen daarna steeds gevaarlijker werd.",
        "expected_terms": [
            "Kristallnacht"
        ]
    },
    {
        "segment_id": "philips_test_01",
        "text": "In het kamp werd gesproken over werk voor Philips en over de rol van de fabriek.",
        "expected_terms": [
            "Philips"
        ]
    }
]


def load_test_segments() -> list[dict]:
    """
    Load test segments from data/test_segments.json.

    If the file does not exist, I use a small default set. This keeps the script
    easy to run during debugging.
    """
    if TEST_SEGMENTS_JSON.exists():
        with open(TEST_SEGMENTS_JSON, "r", encoding="utf-8") as file:
            return json.load(file)

    return DEFAULT_TEST_SEGMENTS


def save_json(results: list[dict]) -> None:
    """
    Save retrieval results as JSON.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    print(f"\nSaved JSON results to: {OUTPUT_JSON}")


def save_csv(results: list[dict]) -> None:
    """
    Save retrieval results as a flat CSV for easier inspection.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "segment_id",
        "rank",
        "label",
        "uri",
        "types",
        "schemes",
        "retrieval_score",
        "candidate_source",
        "retrieval_reason",
    ]

    rows = []

    for result in results:
        segment_id = result["segment_id"]

        for rank, candidate in enumerate(result.get("candidates", []), start=1):
            rows.append({
                "segment_id": segment_id,
                "rank": rank,
                "label": candidate.get("label", ""),
                "uri": candidate.get("uri", ""),
                "types": " | ".join(candidate.get("types", [])),
                "schemes": " | ".join(candidate.get("schemes", [])),
                "retrieval_score": candidate.get("retrieval_score", ""),
                "candidate_source": candidate.get("candidate_source", ""),
                "retrieval_reason": candidate.get("retrieval_reason", ""),
            })

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved CSV results to: {OUTPUT_CSV}")


def print_results(results: list[dict]) -> None:
    """
    Print retrieval results to the terminal.
    """
    for result in results:
        print("\n" + "=" * 100)
        print(f"SEGMENT: {result['segment_id']}")
        print(result["text"])

        print("\nTOP CANDIDATES:")

        for index, candidate in enumerate(result.get("candidates", []), start=1):
            label = candidate.get("label", "")
            types = ", ".join(candidate.get("types", []))
            schemes = ", ".join(candidate.get("schemes", []))
            score = candidate.get("retrieval_score", "")
            source = candidate.get("candidate_source", "")
            reason = candidate.get("retrieval_reason", "")
            uri = candidate.get("uri", "")

            print(
                f"{index:02d}. {label} | types={types} | schemes={schemes} | "
                f"score={score} | source={source} | reason={reason} | uri={uri}"
            )

        expected_terms = result.get("expected_terms", [])

        if expected_terms:
            found_labels = {
                candidate.get("label", "").lower()
                for candidate in result.get("candidates", [])
            }

            print("\nEXPECTED TERMS FOUND?")

            for term in expected_terms:
                is_found = any(term.lower() in label for label in found_labels)
                print(f"- {term}: {'YES' if is_found else 'NO'}")


def main() -> None:
    """
    Run retrieval on the small debugging examples.
    """
    print("Loading thesaurus...")

    concepts_by_id, searchable_labels = load_thesaurus(str(THESAURUS_CSV))

    print(f"Loaded concepts: {len(concepts_by_id)}")
    print(f"Loaded searchable labels: {len(searchable_labels)}")

    test_segments = load_test_segments()
    results = []

    for segment in test_segments:
        segment_id = segment["segment_id"]
        text = segment["text"]

        candidates = retrieve_candidates(
            segment_text=text,
            concepts_by_id=concepts_by_id,
            searchable_labels=searchable_labels,
            top_k=40
        )

        results.append({
            "segment_id": segment_id,
            "segment_title": segment.get("segment_title", ""),
            "text": text,
            "expected_terms": segment.get("expected_terms", []),
            "candidates": candidates,
        })

    print_results(results)
    save_json(results)
    save_csv(results)


if __name__ == "__main__":
    main()