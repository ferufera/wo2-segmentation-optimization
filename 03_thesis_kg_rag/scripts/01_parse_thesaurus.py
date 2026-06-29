"""
01_parse_thesaurus.py

Step 1 of the KG-RAG thesis pipeline.

This script parses the WO2 Thesaurus RDF export and converts it into a flat CSV
table that is easier to use for retrieval.

Input:
    data/export.nt

Output:
    data/thesaurus_concepts.csv

The output CSV contains:
    - Concept URI
    - Concept ID
    - Name / Label
    - Concept Type
    - Broader Concepts
    - Narrower Concepts
    - Related Concepts
    - In Scheme

Why I do this:
    The original WO2 Thesaurus is stored as RDF triples. That is useful as a
    knowledge graph, but for the first KG-RAG prototype I need a simpler table
    that can be searched and used for candidate retrieval.
"""

import csv
from collections import defaultdict
from pathlib import Path

import rdflib


BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_RDF = BASE_DIR / "data" / "export.nt"
OUTPUT_CSV = BASE_DIR / "data" / "thesaurus_concepts.csv"


def get_local_id(uri: str) -> str:
    """
    Extract the local ID from a URI.

    Example:
        https://data.niod.nl/WO2_Thesaurus/events/4354
    becomes:
        4354
    """
    uri = str(uri).strip()

    if not uri:
        return ""

    return uri.rstrip("/").split("/")[-1].split("#")[-1]


def clean_literal(value) -> str:
    """
    Convert RDF literal/object values to clean strings.
    """
    return str(value).strip()


def parse_rdf_to_rows(rdf_path: Path) -> list[dict]:
    """
    Parse the RDF graph and flatten relevant SKOS/RDF relationships.
    """
    if not rdf_path.exists():
        raise FileNotFoundError(f"RDF file not found: {rdf_path}")

    print("Loading the Knowledge Graph... this might take a minute.")

    graph = rdflib.Graph()
    graph.parse(rdf_path, format="nt")

    concepts = defaultdict(lambda: {
        "labels": set(),
        "types": set(),
        "broader": set(),
        "narrower": set(),
        "related": set(),
        "schemes": set(),
    })

    print("Flattening relationships...")

    for subject, predicate, obj in graph:
        subject_uri = str(subject)
        predicate_str = str(predicate).lower()
        object_str = str(obj)

        if "label" in predicate_str:
            concepts[subject_uri]["labels"].add(clean_literal(obj))

        elif predicate_str.endswith("type"):
            concepts[subject_uri]["types"].add(get_local_id(object_str))

        elif "broader" in predicate_str:
            concepts[subject_uri]["broader"].add(get_local_id(object_str))

        elif "narrower" in predicate_str:
            concepts[subject_uri]["narrower"].add(get_local_id(object_str))

        elif "related" in predicate_str:
            concepts[subject_uri]["related"].add(get_local_id(object_str))

        elif "inscheme" in predicate_str:
            concepts[subject_uri]["schemes"].add(get_local_id(object_str))

    print("Building CSV...")

    rows = []

    for uri, data in concepts.items():
        if not data["labels"]:
            continue

        rows.append({
            "Concept URI": uri,
            "Concept ID": get_local_id(uri),
            "Name / Label": " | ".join(sorted(data["labels"])),
            "Concept Type": " | ".join(sorted(data["types"])),
            "Broader Concepts": " | ".join(sorted(data["broader"])),
            "Narrower Concepts": " | ".join(sorted(data["narrower"])),
            "Related Concepts": " | ".join(sorted(data["related"])),
            "In Scheme": " | ".join(sorted(data["schemes"])),
        })

    rows = sorted(rows, key=lambda row: row["Concept URI"])

    return rows


def save_csv(rows: list[dict], output_path: Path) -> None:
    """
    Save flattened thesaurus concepts to CSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "Concept URI",
        "Concept ID",
        "Name / Label",
        "Concept Type",
        "Broader Concepts",
        "Narrower Concepts",
        "Related Concepts",
        "In Scheme",
    ]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Success! Exported {len(rows)} concepts to:")
    print(output_path)


def main() -> None:
    """
    Run RDF parsing and CSV export.
    """
    rows = parse_rdf_to_rows(INPUT_RDF)
    save_csv(rows, OUTPUT_CSV)


if __name__ == "__main__":
    main()