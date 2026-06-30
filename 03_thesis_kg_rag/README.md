# KG-RAG Thesis Pipeline

This folder contains the bachelor thesis pipeline for testing whether retrieval from the WO2 Thesaurus can improve LLM-based concept linking for Dutch Second World War oral history segments.

The thesis compares three concept-linking conditions on the same selected WO2Net oral history segments:

1. **Baseline prompting**
   Uses the original candidate concepts from the previous WO2 oral history matching pipeline and applies the archived baseline prompt logic.

2. **Refined prompting**
   Uses the same original candidate concepts, but applies stricter prompt logic developed during earlier prompt-refinement work.

3. **KG-RAG prompting**
   Retrieves additional candidate concepts from the WO2 Thesaurus before LLM-based concept selection.

All three conditions should be run with the same GPT model so that the comparison focuses on the method setup rather than model choice.

---

## Pipeline Scripts

### `01_parse_thesaurus.py`

Parses the WO2 Thesaurus RDF export into a local structured file, such as:

```text
data/thesaurus_concepts.csv
```

This parsed thesaurus file is used by the retrieval scripts.

### `02_test_retrieval_on_examples.py`

Tests the candidate retrieval logic on small debugging examples before applying it to real WO2Net segments.

### `03_select_evaluation_segments.py`

Creates a shortlist of real WO2Net segments from enriched segment data and crowd validation data. This script is used to select the five evaluation cases for the thesis.

### `04_run_candidate_retrieval.py`

Retrieves WO2 Thesaurus candidate concepts for the selected evaluation segments.

### `05_build_kg_rag_prompts.py`

Builds KG-RAG concept-selection prompts from the selected segment text and retrieved thesaurus candidates.

### `08_build_refined_prompts.py`

Builds refined prompts using the original WO2Net candidate concepts and stricter prompt-selection logic.

### `10_build_baseline_prompts.py`

Builds baseline prompts using the original WO2Net candidate concepts and archived baseline prompt logic.

### `14_process_expert_evaluation.py`

Processes expert questionnaire responses and generates summary tables used in the thesis results section.

---

## Helper Files

### `retrieve_candidates.py`

Contains the KG-RAG candidate retrieval logic. The retrieval setup includes:

* original seed concepts
* explicit lexical retrieval
* contextual event retrieval
* conservative event graph expansion

### `kg_rag_prompts.py`

Contains the KG-RAG prompt builder used to create concept-selection prompts from retrieved candidates.

---

## Main Comparison

The thesis evaluates the outputs of the three conditions using blind expert ratings.

Experts rated proposed concept links for:

* correctness
* specificity

The evaluation was blind: experts did not see whether a concept came from baseline prompting, refined prompting, KG-RAG, or more than one condition.

---

## Data and Privacy Note

The data used by this thesis pipeline is not included in this repository because it may contain WO2Net-derived interview text, validation information, expert evaluation responses, or other restricted research material.

The following folders may exist locally but are not uploaded to GitHub:

```text
data/
results/
```

These folders may contain:

* selected WO2Net evaluation segments
* enriched segment files
* validation data
* generated prompts containing interview excerpts
* raw or processed LLM outputs
* expert questionnaire responses
* processed expert evaluation files

This folder documents the workflow and scripts, but it does not redistribute the underlying WO2Net data.
