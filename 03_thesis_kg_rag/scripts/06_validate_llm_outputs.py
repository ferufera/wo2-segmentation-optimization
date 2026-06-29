"""
06_validate_llm_outputs.py

Step 6 of the KG-RAG thesis pipeline.

This script validates and cleans manual LLM outputs from the KG-RAG concept
selection step.

Why I need this:
    In the first manual test, the model returned correct JSON structure, but some
    URI fields were formatted as Markdown links instead of plain URI strings.
    That is not suitable for later automatic analysis.

This script:
    1. Reads manual LLM output JSON files.
    2. Cleans Markdown-formatted URI values.
    3. Checks whether selected concept URIs were present in the retrieved KG-RAG
       candidate list when candidate data is available.
    4. Saves cleaned JSON files.
    5. Creates a CSV summary for inspection.

Input:
    results/llm_outputs/
    results/candidate_outputs/test_retrieval_candidates.json
    results/candidate_outputs/evaluation_candidates.json

Output:
    results/llm_outputs_cleaned/
    results/validation_reports/llm_output_summary.csv
"""

import csv
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

LLM_OUTPUT_DIR = BASE_DIR / "results" / "llm_outputs"
CLEANED_OUTPUT_DIR = BASE_DIR / "results" / "llm_outputs_cleaned"

CANDIDATE_OUTPUT_DIR = BASE_DIR / "results" / "candidate_outputs"
TEST_CANDIDATES_JSON = CANDIDATE_OUTPUT_DIR / "test_retrieval_candidates.json"
EVALUATION_CANDIDATES_JSON = CANDIDATE_OUTPUT_DIR / "evaluation_candidates.json"

REPORT_DIR = BASE_DIR / "results" / "validation_reports"
SUMMARY_CSV = REPORT_DIR / "llm_output_summary.csv"


def clean_uri(uri_value: str) -> str:
    """
    Clean a URI value returned by the LLM.

    Desired format:
        https://data.niod.nl/WO2_Thesaurus/events/4354

    Possible wrong format:
        [https://data.niod.nl/...](https://data.niod.nl/...)
    """
    if not uri_value:
        return ""

    uri_value = str(uri_value).strip()

    markdown_match = re.match(
        r"\[(https?://[^\]]+)\]\((https?://[^)]+)\)",
        uri_value
    )

    if markdown_match:
        return markdown_match.group(2)

    url_match = re.search(r"https?://[^\s\])]+", uri_value)

    if url_match:
        return url_match.group(0)

    return uri_value


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


def load_candidate_results() -> dict:
    """
    Load candidate results from available candidate output files.

    Returns:
        {
          segment_id: {
            candidate_uris: set(...),
            candidate_by_uri: {...}
          }
        }
    """
    candidate_files = [
        TEST_CANDIDATES_JSON,
        EVALUATION_CANDIDATES_JSON,
    ]

    lookup = {}

    for candidate_file in candidate_files:
        if not candidate_file.exists():
            continue

        with open(candidate_file, "r", encoding="utf-8") as file:
            candidate_results = json.load(file)

        for segment_result in candidate_results:
            segment_id = segment_result.get("segment_id")

            if not segment_id:
                continue

            if segment_id not in lookup:
                lookup[segment_id] = {
                    "candidate_uris": set(),
                    "candidate_by_uri": {},
                }

            for candidate in segment_result.get("candidates", []):
                uri = candidate.get("uri", "")

                if not uri:
                    continue

                lookup[segment_id]["candidate_uris"].add(uri)
                lookup[segment_id]["candidate_by_uri"][uri] = candidate

    return lookup


def load_llm_output_files() -> list[Path]:
    """
    Load manual LLM output JSON files.

    This supports:
        results/llm_outputs/*.json

    Later, if outputs are placed into subfolders, this also supports:
        results/llm_outputs/**/*.json
    """
    if not LLM_OUTPUT_DIR.exists():
        raise FileNotFoundError(f"LLM output folder not found: {LLM_OUTPUT_DIR}")

    files = sorted(LLM_OUTPUT_DIR.glob("**/*.json"))

    files = [
        file for file in files
        if not file.name.endswith("_metadata.json")
    ]

    return files


def infer_condition_from_path(path: Path) -> str:
    """
    Infer condition from folder or filename.

    This prepares the script for later baseline/refined/KG-RAG comparisons.
    """
    path_text = str(path).lower()

    if "kg_rag" in path_text:
        return "kg_rag"

    if "baseline" in path_text:
        return "baseline"

    if "refined" in path_text:
        return "refined"

    return "unknown"


def clean_one_output(output_data: dict) -> dict:
    """
    Clean URI values inside one LLM output dictionary.
    """
    cleaned = dict(output_data)

    cleaned_selected = []

    for concept in output_data.get("selected_concepts", []):
        cleaned_concept = dict(concept)
        cleaned_concept["uri"] = clean_uri(cleaned_concept.get("uri", ""))
        cleaned_selected.append(cleaned_concept)

    cleaned["selected_concepts"] = cleaned_selected

    return cleaned


def save_cleaned_output(segment_id: str, condition: str, cleaned_data: dict) -> Path:
    """
    Save one cleaned JSON file.
    """
    CLEANED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_filename(segment_id)}_{condition}_llm_output_cleaned.json"
    output_path = CLEANED_OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(cleaned_data, file, indent=2, ensure_ascii=False)

    return output_path


def build_summary_rows(
    cleaned_data: dict,
    condition: str,
    candidate_lookup: dict
) -> list[dict]:
    """
    Build CSV summary rows for one cleaned LLM output.
    """
    segment_id = cleaned_data.get("segment_id", "")

    segment_candidates = candidate_lookup.get(segment_id, {})
    candidate_uris = segment_candidates.get("candidate_uris", set())
    candidate_by_uri = segment_candidates.get("candidate_by_uri", {})

    rows = []

    for concept in cleaned_data.get("selected_concepts", []):
        uri = concept.get("uri", "")
        label = concept.get("label", "")
        confidence = concept.get("confidence", "")
        evidence = concept.get("evidence", "")
        reason = concept.get("reason", "")

        uri_in_candidate_list = ""

        if segment_id in candidate_lookup:
            uri_in_candidate_list = uri in candidate_uris

        candidate_info = candidate_by_uri.get(uri, {})

        rows.append({
            "segment_id": segment_id,
            "condition": condition,
            "selected_label": label,
            "selected_uri": uri,
            "confidence": confidence,
            "evidence": evidence,
            "llm_reason": reason,
            "uri_in_candidate_list": uri_in_candidate_list,
            "retrieval_score": candidate_info.get("retrieval_score", ""),
            "candidate_source": candidate_info.get("candidate_source", ""),
            "retrieval_reason": candidate_info.get("retrieval_reason", ""),
        })

    return rows


def save_summary_csv(rows: list[dict]) -> None:
    """
    Save all selected concept summary rows to CSV.
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "segment_id",
        "condition",
        "selected_label",
        "selected_uri",
        "confidence",
        "evidence",
        "llm_reason",
        "uri_in_candidate_list",
        "retrieval_score",
        "candidate_source",
        "retrieval_reason",
    ]

    with open(SUMMARY_CSV, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved summary CSV: {SUMMARY_CSV}")


def main() -> None:
    """
    Validate and clean all manual LLM outputs.
    """
    candidate_lookup = load_candidate_results()
    output_files = load_llm_output_files()

    if not output_files:
        print(f"No LLM output JSON files found in: {LLM_OUTPUT_DIR}")
        return

    all_summary_rows = []

    for output_file in output_files:
        print(f"Processing: {output_file}")

        with open(output_file, "r", encoding="utf-8") as file:
            output_data = json.load(file)

        cleaned_data = clean_one_output(output_data)

        segment_id = cleaned_data.get("segment_id", output_file.stem)
        condition = infer_condition_from_path(output_file)

        cleaned_path = save_cleaned_output(
            segment_id=segment_id,
            condition=condition,
            cleaned_data=cleaned_data
        )

        print(f"Saved cleaned output: {cleaned_path}")

        summary_rows = build_summary_rows(
            cleaned_data=cleaned_data,
            condition=condition,
            candidate_lookup=candidate_lookup
        )

        all_summary_rows.extend(summary_rows)

    save_summary_csv(all_summary_rows)

    print("\nDone. LLM outputs were cleaned and summarized.")


if __name__ == "__main__":
    main()