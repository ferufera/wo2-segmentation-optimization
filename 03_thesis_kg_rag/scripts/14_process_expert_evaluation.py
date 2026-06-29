"""
Process the WO2Net expert evaluation questionnaires.

This script turns the filled expert evaluation workbooks into the analysis files
used in the thesis. It is designed to be rerunnable: if more expert responses are
added later, the script can be run again with the same internal evaluation table
and a larger response folder.

Inputs
------
1. internal_expert_evaluation_table.csv
   The internal table contains concept metadata and hidden method provenance.
   It must include concept_id and the selected_by_* columns.

2. Expert questionnaire workbooks
   By default, the script looks for files matching expert_*_response_raw.xlsx.
   Each workbook is expected to use the questionnaire columns:
   case_id, concept_id, segment_excerpt, concept_label, concept_uri,
   correctness, specificity, missing_concept_comment, general_comment.

3. Optional follow-up comments CSV
   This is useful when an expert sends a broader reflection by email after the
   questionnaire. The comment is kept separate from the structured ratings and
   included only in the qualitative comment-theme file.

Outputs
-------
- combined_expert_ratings.csv
- expert_rating_summary_by_method.csv
- expert_rating_summary_by_case.csv
- expert_rating_summary_by_concept.csv
- expert_comment_themes.csv
- expert_evaluation_processing_notes.txt

The script uses only the Python standard library. It reads xlsx files directly as
zipped XML files, so no spreadsheet package is required.
"""

from __future__ import annotations

import argparse
import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
METHODS = ["baseline", "refined", "kg_rag"]
CORRECTNESS_PRIORITY = ["correct", "partially correct", "incorrect", "unsure", "missing"]
SPECIFICITY_PRIORITY = ["appropriate", "too broad", "too narrow", "not applicable", "unsure", "missing"]
QUESTIONNAIRE_COLUMNS = [
    "case_id",
    "concept_id",
    "segment_excerpt",
    "concept_label",
    "concept_uri",
    "correctness",
    "specificity",
    "missing_concept_comment",
    "general_comment",
]


def clean(value: object) -> str:
    """Return a stripped string and convert missing values to an empty string."""
    if value is None:
        return ""
    return str(value).strip()


def normalize_rating(value: object) -> str:
    """Normalize questionnaire ratings to lowercase strings used in the output tables."""
    return clean(value).lower() or "missing"


def normalize_bool(value: object) -> bool:
    """Interpret boolean-like values from CSV exports."""
    return clean(value).lower() in {"true", "1", "yes", "y"}


def excel_column_to_index(column_letters: str) -> int:
    """Convert Excel column letters, such as A or AB, to a zero-based index."""
    index = 0
    for letter in column_letters:
        index = index * 26 + ord(letter.upper()) - 64
    return index - 1


def read_xlsx_first_sheet(path: Path) -> List[Tuple[int, List[str]]]:
    """Read the first worksheet of an xlsx file as row values.

    The raw expert workbooks are not modified. The function reads shared strings
    and inline strings from the workbook XML and returns a list of
    ``(excel_row_number, row_values)`` pairs.
    """
    rows: List[Tuple[int, List[str]]] = []

    with zipfile.ZipFile(path) as workbook_zip:
        names = set(workbook_zip.namelist())

        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(workbook_zip.read("xl/sharedStrings.xml"))
            for item in root.findall(XLSX_NS + "si"):
                shared_strings.append("".join(t.text or "" for t in item.iter(XLSX_NS + "t")))

        sheet_path = "xl/worksheets/sheet1.xml"
        if sheet_path not in names:
            raise FileNotFoundError(f"{path.name} does not contain {sheet_path}")

        root = ET.fromstring(workbook_zip.read(sheet_path))
        for row in root.findall(".//" + XLSX_NS + "row"):
            row_number = int(row.attrib.get("r", "0"))
            values_by_column: Dict[int, str] = {}

            for cell in row.findall(XLSX_NS + "c"):
                cell_ref = cell.attrib.get("r", "")
                match = re.match(r"([A-Z]+)(\d+)", cell_ref)
                if not match:
                    continue

                column_index = excel_column_to_index(match.group(1))
                cell_type = cell.attrib.get("t")
                value = ""

                if cell_type == "inlineStr":
                    value = "".join(t.text or "" for t in cell.iter(XLSX_NS + "t"))
                else:
                    value_node = cell.find(XLSX_NS + "v")
                    if value_node is not None:
                        raw_value = value_node.text or ""
                        if cell_type == "s":
                            try:
                                value = shared_strings[int(raw_value)]
                            except (IndexError, ValueError):
                                value = raw_value
                        elif cell_type == "b":
                            value = "TRUE" if raw_value == "1" else "FALSE"
                        else:
                            value = raw_value

                values_by_column[column_index] = value

            if values_by_column:
                max_column = max(values_by_column)
                row_values = [values_by_column.get(i, "") for i in range(max_column + 1)]
                rows.append((row_number, row_values))

    return rows


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    """Read a UTF-8 or UTF-8-BOM CSV file into a list of dictionaries."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, object]]) -> None:
    """Write dictionaries to a CSV file with a stable column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def discover_expert_files(input_dir: Path, pattern: str) -> List[Tuple[str, Path]]:
    """Find expert response workbooks and assign stable anonymized expert IDs.

    If filenames already start with expert_01, expert_02, etc., those IDs are
    preserved. Otherwise, IDs are assigned according to sorted filename order.
    """
    files = sorted(input_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No expert files found in {input_dir} with pattern {pattern!r}")

    discovered: List[Tuple[str, Path]] = []
    used_ids = set()

    for index, path in enumerate(files, start=1):
        match = re.match(r"(expert_\d+)", path.stem.lower())
        expert_id = match.group(1) if match else f"expert_{index:02d}"

        # Avoid accidental duplicate expert IDs if files are named inconsistently.
        if expert_id in used_ids:
            expert_id = f"expert_{index:02d}"
        used_ids.add(expert_id)
        discovered.append((expert_id, path))

    return discovered


def score_correctness(value: str) -> object:
    """Convert correctness labels to numeric values for partial-credit summaries."""
    rating = normalize_rating(value)
    if rating == "correct":
        return 1.0
    if rating == "partially correct":
        return 0.5
    if rating == "incorrect":
        return 0.0
    return ""


def score_specificity(value: str) -> object:
    """Convert specificity labels to numeric values for applicable specificity summaries."""
    rating = normalize_rating(value)
    if rating == "appropriate":
        return 1.0
    if rating in {"too broad", "too narrow"}:
        return 0.0
    return ""


def majority(counter: Counter, priority: Sequence[str]) -> str:
    """Return a deterministic majority label, using priority order to break ties."""
    if not counter:
        return ""
    highest = max(counter.values())
    tied_labels = [label for label, count in counter.items() if count == highest]
    for label in priority:
        if label in tied_labels:
            return label
    return tied_labels[0]


def classify_comment(text: str) -> str:
    """Assign lightweight qualitative theme codes to an expert comment.

    The goal is not to replace manual qualitative interpretation. The theme codes
    make it easier to group recurring issues before writing the Results and
    Discussion sections.
    """
    lowered = (text or "").lower()
    themes: List[str] = []

    keyword_groups = [
        (
            "alternative_or_missing_concept_suggestion",
            ["http", "concept", "keyword", "label", "suggest", "alternative", "missing", "toevoegen", "ontbrek"],
        ),
        (
            "specificity_level_issue",
            ["too broad", "broad", "specific", "specif", "narrow", "more precise", "precise"],
        ),
        (
            "incidental_or_not_central_concept",
            ["not the subject", "sideline", "only mentioned", "not visited", "not really relevant", "maybe", "technical list"],
        ),
        (
            "camp_or_place_disambiguation",
            ["bergen", "birkenau", "auschwitz", "sobibor", "westerbork", "vught", "camp", "kamp", "belsen"],
        ),
        (
            "need_for_wider_interview_context",
            ["whole interview", "complete interview", "context", "excerpt", "without that information", "fragment"],
        ),
        (
            "broader_thematic_annotation",
            ["trauma", "persecution", "emigration", "religious", "anti jewish", "anti-jewish", "measures", "measurements"],
        ),
        (
            "multilingual_label_or_duplicate_issue",
            ["german", "dutch", "english", "multilingual", "duplicate", "doubles", "language"],
        ),
        (
            "incorrect_or_confusing_label",
            ["incorrect", "confusion", "confusing", "would not use", "wrong"],
        ),
    ]

    for theme, keywords in keyword_groups:
        if any(keyword in lowered for keyword in keywords):
            themes.append(theme)

    if not themes:
        themes.append("general_expert_comment")

    return "; ".join(dict.fromkeys(themes))


def build_header_index(header_row: Sequence[str]) -> Dict[str, int]:
    """Map questionnaire column names to row positions."""
    header_index = {clean(name): index for index, name in enumerate(header_row)}
    missing_columns = [column for column in QUESTIONNAIRE_COLUMNS if column not in header_index]
    if missing_columns:
        raise ValueError(f"Questionnaire header is missing expected columns: {missing_columns}")
    return header_index


def get_cell(row_values: Sequence[str], header_index: Dict[str, int], column: str) -> str:
    """Return a cell value by questionnaire column name."""
    index = header_index[column]
    if index >= len(row_values):
        return ""
    return clean(row_values[index])


def parse_expert_workbook(
    expert_id: str,
    workbook_path: Path,
    internal_by_concept_id: Dict[str, Dict[str, str]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    """Parse one expert workbook into structured ratings and comment rows."""
    workbook_rows = read_xlsx_first_sheet(workbook_path)
    if not workbook_rows:
        raise ValueError(f"{workbook_path.name} has no readable rows")

    header_index = build_header_index(workbook_rows[0][1])
    ratings: List[Dict[str, object]] = []
    comments: List[Dict[str, object]] = []
    last_case_id = ""

    for excel_row_number, row_values in workbook_rows[1:]:
        concept_id = get_cell(row_values, header_index, "concept_id")

        if concept_id.startswith("case_") and concept_id in internal_by_concept_id:
            metadata = internal_by_concept_id[concept_id]
            last_case_id = metadata.get("case_id", "")

            correctness = normalize_rating(get_cell(row_values, header_index, "correctness"))
            specificity = normalize_rating(get_cell(row_values, header_index, "specificity"))
            missing_comment = get_cell(row_values, header_index, "missing_concept_comment")
            general_comment = get_cell(row_values, header_index, "general_comment")

            methods_selected_by = [
                method
                for method in METHODS
                if normalize_bool(metadata.get(f"selected_by_{method}", ""))
            ]

            record = {
                "expert_id": expert_id,
                "source_file": workbook_path.name,
                "source_excel_row": excel_row_number,
                "case_id": metadata.get("case_id", ""),
                "concept_id": concept_id,
                "segment_id": metadata.get("segment_id", ""),
                "pilot_role": metadata.get("pilot_role", ""),
                "segment_excerpt": metadata.get("segment_excerpt", ""),
                "concept_label": metadata.get("concept_label", ""),
                "concept_uri": metadata.get("concept_uri", ""),
                "selected_by_baseline": metadata.get("selected_by_baseline", ""),
                "selected_by_refined": metadata.get("selected_by_refined", ""),
                "selected_by_kg_rag": metadata.get("selected_by_kg_rag", ""),
                "baseline_score": metadata.get("baseline_score", ""),
                "refined_score": metadata.get("refined_score", ""),
                "kg_rag_score": metadata.get("kg_rag_score", ""),
                "methods_selected_by": "; ".join(methods_selected_by),
                "correctness": correctness,
                "specificity": specificity,
                "correctness_numeric": score_correctness(correctness),
                "specificity_numeric": score_specificity(specificity),
                "missing_concept_comment": missing_comment,
                "general_comment": general_comment,
            }
            ratings.append(record)

            for comment_field in ["missing_concept_comment", "general_comment"]:
                comment_text = clean(record[comment_field])
                if comment_text:
                    comments.append(
                        {
                            "comment_id": f"{expert_id}_{concept_id}_{comment_field}",
                            "expert_id": expert_id,
                            "source_type": comment_field,
                            "case_id": record["case_id"],
                            "concept_id": concept_id,
                            "concept_label": record["concept_label"],
                            "concept_uri": record["concept_uri"],
                            "comment_text": comment_text,
                            "theme_codes": classify_comment(comment_text),
                        }
                    )
        else:
            # Inserted rows are not normal rating rows, but they may contain useful qualitative notes.
            non_empty_cells = [clean(value) for value in row_values if clean(value)]
            comment_text = " | ".join(non_empty_cells)
            if comment_text:
                comments.append(
                    {
                        "comment_id": f"{expert_id}_extra_row_{excel_row_number}",
                        "expert_id": expert_id,
                        "source_type": "inserted_extra_row",
                        "case_id": last_case_id,
                        "concept_id": "",
                        "concept_label": "",
                        "concept_uri": "",
                        "comment_text": comment_text,
                        "theme_codes": classify_comment(comment_text),
                    }
                )

    return ratings, comments


def read_follow_up_comments(path: Path) -> List[Dict[str, object]]:
    """Read optional follow-up email comments and convert them to theme rows."""
    if not path or not path.exists():
        return []

    rows = read_csv_dicts(path)
    comment_rows: List[Dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        comment_text = clean(row.get("comment_text", ""))
        if not comment_text:
            continue

        expert_id = clean(row.get("expert_id", "")) or f"follow_up_{index:02d}"
        source_type = clean(row.get("source_type", "")) or "follow_up_email"
        case_id = clean(row.get("case_id", "")) or "multiple"
        concept_id = clean(row.get("concept_id", ""))
        concept_label = clean(row.get("concept_label", ""))
        concept_uri = clean(row.get("concept_uri", ""))

        comment_rows.append(
            {
                "comment_id": f"{expert_id}_{source_type}_{index:02d}",
                "expert_id": expert_id,
                "source_type": source_type,
                "case_id": case_id,
                "concept_id": concept_id,
                "concept_label": concept_label,
                "concept_uri": concept_uri,
                "comment_text": comment_text,
                "theme_codes": classify_comment(comment_text),
            }
        )
    return comment_rows


def aggregate_records(records: Sequence[Dict[str, object]]) -> Dict[str, object]:
    """Calculate descriptive summary statistics for a set of expert ratings."""
    total = len(records)
    correctness_counts = Counter(clean(record.get("correctness", "missing")) or "missing" for record in records)
    specificity_counts = Counter(clean(record.get("specificity", "missing")) or "missing" for record in records)

    correctness_scores = [
        float(record["correctness_numeric"])
        for record in records
        if record.get("correctness_numeric", "") != ""
    ]
    specificity_scores = [
        float(record["specificity_numeric"])
        for record in records
        if record.get("specificity_numeric", "") != ""
    ]
    applicable_specificity_records = [
        record
        for record in records
        if clean(record.get("specificity", "")) not in {"not applicable", "unsure", "missing", ""}
    ]

    return {
        "n_expert_ratings": total,
        "n_unique_concept_rows": len({clean(record.get("concept_id", "")) for record in records}),
        "n_unique_concept_uris": len({clean(record.get("concept_uri", "")) for record in records}),
        "correct_count": correctness_counts.get("correct", 0),
        "partially_correct_count": correctness_counts.get("partially correct", 0),
        "incorrect_count": correctness_counts.get("incorrect", 0),
        "correctness_unsure_count": correctness_counts.get("unsure", 0),
        "correctness_missing_count": correctness_counts.get("missing", 0),
        "strict_correct_rate_all_ratings": round(correctness_counts.get("correct", 0) / total, 4) if total else "",
        "partial_credit_correctness_score": round(sum(correctness_scores) / len(correctness_scores), 4) if correctness_scores else "",
        "appropriate_count": specificity_counts.get("appropriate", 0),
        "too_broad_count": specificity_counts.get("too broad", 0),
        "too_narrow_count": specificity_counts.get("too narrow", 0),
        "not_applicable_count": specificity_counts.get("not applicable", 0),
        "specificity_unsure_count": specificity_counts.get("unsure", 0),
        "specificity_missing_count": specificity_counts.get("missing", 0),
        "appropriate_rate_all_ratings": round(specificity_counts.get("appropriate", 0) / total, 4) if total else "",
        "appropriate_rate_applicable_only": (
            round(specificity_counts.get("appropriate", 0) / len(applicable_specificity_records), 4)
            if applicable_specificity_records
            else ""
        ),
        "specificity_score_applicable_only": (
            round(sum(specificity_scores) / len(specificity_scores), 4) if specificity_scores else ""
        ),
    }


def expand_by_method(combined: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Duplicate each expert rating once for every method that selected the concept."""
    method_records: List[Dict[str, object]] = []
    for record in combined:
        for method in METHODS:
            if normalize_bool(record.get(f"selected_by_{method}", "")):
                method_record = dict(record)
                method_record["method"] = method
                method_record["method_score"] = record.get(f"{method}_score", "")
                method_records.append(method_record)
    return method_records


def create_method_summary(method_records: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Summarize expert ratings by method."""
    rows: List[Dict[str, object]] = []
    for method in METHODS:
        records = [record for record in method_records if record.get("method") == method]
        summary = {"method": method}
        summary.update(aggregate_records(records))
        rows.append(summary)
    return rows


def create_case_summary(method_records: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Summarize expert ratings by case and method."""
    rows: List[Dict[str, object]] = []
    case_ids = sorted({clean(record.get("case_id", "")) for record in method_records})
    for case_id in case_ids:
        case_records = [record for record in method_records if record.get("case_id") == case_id]
        if not case_records:
            continue
        case_metadata = case_records[0]
        for method in METHODS:
            records = [record for record in case_records if record.get("method") == method]
            summary = {
                "case_id": case_id,
                "segment_id": case_metadata.get("segment_id", ""),
                "pilot_role": case_metadata.get("pilot_role", ""),
                "method": method,
            }
            summary.update(aggregate_records(records))
            rows.append(summary)
    return rows


def create_concept_summary(combined: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Summarize expert ratings by case and concept URI.

    The grouping uses case + URI, not label alone. This supports URI-based
    normalization when the same concept appears with different labels or languages.
    """
    groups: Dict[Tuple[str, str], List[Dict[str, object]]] = defaultdict(list)
    for record in combined:
        key = clean(record.get("concept_uri", "")) or clean(record.get("concept_label", ""))
        groups[(clean(record.get("case_id", "")), key)].append(record)

    rows: List[Dict[str, object]] = []
    for (case_id, key), records in sorted(groups.items(), key=lambda item: (item[0][0], item[1][0].get("concept_label", ""))):
        first = records[0]
        correctness_counts = Counter(clean(record.get("correctness", "missing")) or "missing" for record in records)
        specificity_counts = Counter(clean(record.get("specificity", "missing")) or "missing" for record in records)
        method_set = sorted(
            {
                method
                for record in records
                for method in clean(record.get("methods_selected_by", "")).split("; ")
                if method
            }
        )
        concept_ids = sorted({clean(record.get("concept_id", "")) for record in records})
        labels = sorted({clean(record.get("concept_label", "")) for record in records})
        comments = []
        for record in records:
            for field in ["missing_concept_comment", "general_comment"]:
                comment = clean(record.get(field, ""))
                if comment:
                    comments.append(f"{record.get('expert_id')}:{field}={comment}")

        summary = {
            "case_id": case_id,
            "segment_id": first.get("segment_id", ""),
            "pilot_role": first.get("pilot_role", ""),
            "concept_uri_or_label_key": key,
            "concept_ids": "; ".join(concept_ids),
            "labels_in_questionnaire": "; ".join(labels),
            "methods_selected_by_any_label": "; ".join(method_set),
            "n_questionnaire_rows_for_uri": len(concept_ids),
            "n_expert_ratings": len(records),
            "majority_correctness": majority(correctness_counts, CORRECTNESS_PRIORITY),
            "majority_specificity": majority(specificity_counts, SPECIFICITY_PRIORITY),
            "expert_comments_combined": " || ".join(comments),
        }
        summary.update(aggregate_records(records))
        rows.append(summary)
    return rows


def build_processing_notes(
    expert_files: Sequence[Tuple[str, Path]],
    combined: Sequence[Dict[str, object]],
    method_records: Sequence[Dict[str, object]],
    comment_rows: Sequence[Dict[str, object]],
    expected_concept_rows: int,
) -> str:
    """Create a compact QA note file for the generated evaluation outputs."""
    lines: List[str] = []
    lines.append(f"Expert files processed: {len(expert_files)}")
    for expert_id, path in expert_files:
        lines.append(f"- {expert_id}: {path.name}")
    lines.append(f"combined_expert_ratings rows: {len(combined)}")
    lines.append(f"expected ratings: {len(expert_files)} experts x {expected_concept_rows} concept rows = {len(expert_files) * expected_concept_rows}")
    lines.append(f"method-expanded ratings: {len(method_records)}")
    lines.append(f"comments/theme rows: {len(comment_rows)}")
    lines.append("")
    lines.append("Missing/blank ratings found:")

    for expert_id, _ in expert_files:
        records = [record for record in combined if record.get("expert_id") == expert_id]
        missing_correctness = [record["concept_id"] for record in records if record.get("correctness") == "missing"]
        missing_specificity = [record["concept_id"] for record in records if record.get("specificity") == "missing"]
        lines.append(f"- {expert_id}: missing correctness={missing_correctness}; missing specificity={missing_specificity}")

    lines.append("")
    lines.append("Rate definitions:")
    lines.append("- strict_correct_rate_all_ratings = correct / all ratings in the group")
    lines.append("- partial_credit_correctness_score excludes unsure and missing ratings; correct=1, partially correct=0.5, incorrect=0")
    lines.append("- appropriate_rate_all_ratings = appropriate / all ratings in the group")
    lines.append("- appropriate_rate_applicable_only excludes not applicable, unsure, missing, and blank specificity ratings")
    lines.append("- specificity_score_applicable_only excludes not applicable, unsure, missing, and blank specificity ratings; appropriate=1, too broad/too narrow=0")

    return "\n".join(lines)


def process_evaluation(args: argparse.Namespace) -> None:
    """Run the full expert evaluation processing workflow."""
    internal_table_path = Path(args.internal_table)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    follow_up_path = Path(args.follow_up_comments) if args.follow_up_comments else None

    internal_rows = read_csv_dicts(internal_table_path)
    if not internal_rows:
        raise ValueError(f"Internal table is empty: {internal_table_path}")

    internal_by_concept_id = {row["concept_id"]: row for row in internal_rows}
    expert_files = discover_expert_files(input_dir, args.expert_pattern)

    combined: List[Dict[str, object]] = []
    comment_rows: List[Dict[str, object]] = []

    for expert_id, workbook_path in expert_files:
        expert_ratings, expert_comments = parse_expert_workbook(expert_id, workbook_path, internal_by_concept_id)
        combined.extend(expert_ratings)
        comment_rows.extend(expert_comments)

    if follow_up_path:
        comment_rows.extend(read_follow_up_comments(follow_up_path))

    method_records = expand_by_method(combined)
    method_summary = create_method_summary(method_records)
    case_summary = create_case_summary(method_records)
    concept_summary = create_concept_summary(combined)

    combined_fields = [
        "expert_id",
        "source_file",
        "source_excel_row",
        "case_id",
        "concept_id",
        "segment_id",
        "pilot_role",
        "concept_label",
        "concept_uri",
        "selected_by_baseline",
        "selected_by_refined",
        "selected_by_kg_rag",
        "baseline_score",
        "refined_score",
        "kg_rag_score",
        "methods_selected_by",
        "correctness",
        "specificity",
        "correctness_numeric",
        "specificity_numeric",
        "missing_concept_comment",
        "general_comment",
        "segment_excerpt",
    ]
    summary_fields = [
        "n_expert_ratings",
        "n_unique_concept_rows",
        "n_unique_concept_uris",
        "correct_count",
        "partially_correct_count",
        "incorrect_count",
        "correctness_unsure_count",
        "correctness_missing_count",
        "strict_correct_rate_all_ratings",
        "partial_credit_correctness_score",
        "appropriate_count",
        "too_broad_count",
        "too_narrow_count",
        "not_applicable_count",
        "specificity_unsure_count",
        "specificity_missing_count",
        "appropriate_rate_all_ratings",
        "appropriate_rate_applicable_only",
        "specificity_score_applicable_only",
    ]
    concept_fields = [
        "case_id",
        "segment_id",
        "pilot_role",
        "concept_uri_or_label_key",
        "concept_ids",
        "labels_in_questionnaire",
        "methods_selected_by_any_label",
        "n_questionnaire_rows_for_uri",
        "n_expert_ratings",
        "majority_correctness",
        "majority_specificity",
        "n_unique_concept_rows",
        "n_unique_concept_uris",
        "correct_count",
        "partially_correct_count",
        "incorrect_count",
        "correctness_unsure_count",
        "correctness_missing_count",
        "strict_correct_rate_all_ratings",
        "partial_credit_correctness_score",
        "appropriate_count",
        "too_broad_count",
        "too_narrow_count",
        "not_applicable_count",
        "specificity_unsure_count",
        "specificity_missing_count",
        "appropriate_rate_all_ratings",
        "appropriate_rate_applicable_only",
        "specificity_score_applicable_only",
        "expert_comments_combined",
    ]
    comment_fields = [
        "comment_id",
        "expert_id",
        "source_type",
        "case_id",
        "concept_id",
        "concept_label",
        "concept_uri",
        "theme_codes",
        "comment_text",
    ]

    write_csv(output_dir / "combined_expert_ratings.csv", combined_fields, combined)
    write_csv(output_dir / "expert_rating_summary_by_method.csv", ["method"] + summary_fields, method_summary)
    write_csv(output_dir / "expert_rating_summary_by_case.csv", ["case_id", "segment_id", "pilot_role", "method"] + summary_fields, case_summary)
    write_csv(output_dir / "expert_rating_summary_by_concept.csv", concept_fields, concept_summary)
    write_csv(output_dir / "expert_comment_themes.csv", comment_fields, comment_rows)

    notes = build_processing_notes(
        expert_files=expert_files,
        combined=combined,
        method_records=method_records,
        comment_rows=comment_rows,
        expected_concept_rows=len(internal_rows),
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "expert_evaluation_processing_notes.txt").write_text(notes, encoding="utf-8")

    print(notes)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Process blind expert evaluation questionnaires and create thesis analysis CSV files."
    )
    parser.add_argument(
        "--input-dir",
        default=".",
        help="Folder containing expert response xlsx files. Default: current directory.",
    )
    parser.add_argument(
        "--internal-table",
        default="internal_expert_evaluation_table.csv",
        help="Path to the internal expert evaluation table with method provenance.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Folder where processed CSV files should be written. Default: current directory.",
    )
    parser.add_argument(
        "--expert-pattern",
        default="expert_*_response_raw.xlsx",
        help="Glob pattern for expert response files inside --input-dir.",
    )
    parser.add_argument(
        "--follow-up-comments",
        default="",
        help="Optional CSV file with broader expert reflections or follow-up email comments.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    process_evaluation(parse_args())
