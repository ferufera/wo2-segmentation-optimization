# KG-RAG Thesis Pipeline

This folder contains the bachelor thesis pipeline for testing whether retrieval from the WO2 Thesaurus can improve LLM-based concept linking for Dutch Second World War oral history segments.

This thesis work was developed independently by **Feruza Bakhtiyorova** as part of the Bachelor Artificial Intelligence thesis:

**Improving Concept Specificity in LLM-Based Concept Linking for Oral History Segments Using the WO2 Thesaurus**

The thesis compares three concept-linking conditions on the same selected WO2Net oral history segments:

1. **Baseline prompting**
   Uses the original candidate concepts from the previous WO2 oral history matching pipeline and applies the archived baseline prompt logic.

2. **Refined prompting**
   Uses the same original candidate concepts, but applies stricter prompt logic developed during earlier prompt-refinement work.

3. **KG-RAG prompting**
   Retrieves additional candidate concepts from the WO2 Thesaurus before LLM-based concept selection.

All three conditions should be run with the same GPT model so that the comparison focuses on the method setup rather than model choice.

---

## Research Question

> To what extent does retrieval from the WO2 Thesaurus improve the correctness and specificity of LLM-based concept linking for oral history segments?

---

## Pipeline Scripts

The thesis pipeline is organised as numbered scripts. Some scripts were used for testing or intermediate inspection, while others produced the final thesis prompts, comparison tables, and expert-evaluation summaries.

| Script                                  | Purpose                                                                                                               | Public status                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| `01_parse_thesaurus.py`                 | Parses the WO2 Thesaurus RDF export into a local structured thesaurus file.                                           | Included                                 |
| `02_test_retrieval_on_examples.py`      | Tests the KG-RAG candidate retrieval logic on small debugging examples before running it on selected WO2Net segments. | Included if examples are dummy/sanitized |
| `03_select_evaluation_segments.py`      | Selects the five evaluation cases from enriched segment data and previous validation data.                            | Included                                 |
| `04_run_candidate_retrieval.py`         | Retrieves WO2 Thesaurus candidate concepts for the selected evaluation segments.                                      | Included                                 |
| `05_build_kg_rag_prompts.py`            | Builds KG-RAG prompts from selected segment excerpts and retrieved thesaurus candidates.                              | Included                                 |
| `06_validate_llm_outputs.py`            | Cleans and validates manually saved LLM outputs and checks whether they can be processed consistently.                | Included                                 |
| `07_summarize_kg_rag_outputs.py`        | Summarizes KG-RAG outputs after LLM concept selection.                                                                | Included                                 |
| `08_build_refined_prompts.py`           | Builds refined prompts using the original WO2Net candidate concepts and stricter prompt logic.                        | Included                                 |
| `09_summarize_refined_outputs.py`       | Summarizes refined-prompting outputs after LLM concept selection.                                                     | Included                                 |
| `10_build_baseline_prompts.py`          | Builds baseline prompts using the original WO2Net candidate concepts and archived baseline prompt logic.              | Included                                 |
| `11_summarize_baseline_outputs.py`      | Summarizes baseline-prompting outputs after LLM concept selection.                                                    | Included                                 |
| `12_create_method_comparison_table.py`  | Creates comparison tables across baseline prompting, refined prompting, and KG-RAG prompting.                         | Included                                 |
| `13_create_expert_evaluation_tables.py` | Creates the blind expert-evaluation tables used for expert review.                                                    | Included                                 |
| `14_process_expert_evaluation.py`       | Processes expert questionnaire responses and generates the final summary tables used in the thesis results.           | Included                                 |

---

## Helper Files

| File                     | Purpose                                                                                                                                                           | Public status                                                                                    |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `retrieve_candidates.py` | Contains the KG-RAG candidate retrieval logic, including original seed concepts, lexical retrieval, contextual event retrieval, and conservative graph expansion. | Included                                                                                         |
| `kg_rag_prompts.py`      | Contains the KG-RAG prompt builder.                                                                                                                               | Included                                                                                         |
| `baseline_prompts.py`    | Contains baseline prompt logic used for the baseline prompting condition.                                                                                         | Included                                                                                         |
| `refined_prompts.py`     | Contains refined prompt logic used for the refined prompting condition.                                                                                           | Included                                                                                         |
| `models.py`              | Contains shared data structures used by the scripts.                                                                                                              | Not included publicly if it depends on WO2Net/project-restricted code or private data structures |

---

## KG-RAG Retrieval Design

In this thesis, KG-RAG means knowledge-graph retrieval-augmented generation. The WO2 Thesaurus is used as a structured retrieval source before the LLM selects final concept links.

The retrieval step uses four layers:

1. **Original seed concepts**
   Concepts already matched by the previous WO2Net pipeline are kept as seed candidates.

2. **Explicit lexical retrieval**
   The segment text is matched against searchable WO2 Thesaurus labels.

3. **Contextual event retrieval**
   Event concepts are retrieved using contextual clues such as dates, months, locations, and event-related words.

4. **Conservative event graph expansion**
   A small number of related or broader event concepts may be added from the thesaurus graph for strong contextual event candidates. This expansion is restricted to event concepts and intentionally limited to reduce noisy matches.

Retrieved candidates are merged by concept ID, ranked, and limited to a maximum of 40 candidates per segment. The LLM then selects only the concepts that are supported by the segment text.

---

## Thesis Data and Evaluation Setup

The thesis uses a focused expert-informed evaluation rather than a large statistical benchmark.

The local thesis pipeline processed:

* 4,761 enriched segments
* 780 validation groups

This produced a shortlist of 487 candidate segments:

* 414 rejected segments
* 38 conflict segments
* 35 accepted segments

From this shortlist, five segments were selected for expert evaluation. These cases represented different concept-linking problems:

* organisation/work concepts
* missing camp concepts
* missing event concept
* an accepted control case
* place/camp disambiguation

The expert evaluation was prepared as a blind questionnaire.

* Five WO2Net experts completed the evaluation.
* The questionnaire contained 44 blind concept rows.
* Experts rated each proposed concept for correctness and specificity.
* Experts did not see whether a concept came from baseline prompting, refined prompting, KG-RAG, or more than one condition.

Method provenance was stored separately and mapped back after the questionnaire responses were collected.

---

## Thesis Results

The thesis found a trade-off.

KG-RAG improved specificity in the selected cases, but it did not improve overall correctness.

| Condition | Expert ratings | Unique concept rows | Strict correct rate | Partial-credit correctness | Appropriate specificity, all ratings | Appropriate specificity, applicable only |
| --------- | -------------: | ------------------: | ------------------: | -------------------------: | -----------------------------------: | ---------------------------------------: |
| Baseline  |            115 |                  23 |              66.96% |                     75.23% |                               54.78% |                                   65.62% |
| Refined   |             95 |                  19 |              68.42% |                     77.47% |                               61.05% |                                   74.36% |
| KG-RAG    |            160 |                  32 |              65.62% |                     74.68% |                               59.38% |                                   79.17% |

KG-RAG achieved the highest applicable-specificity rate, meaning that experts more often judged its concepts to be at the right level of detail when specificity was applicable. However, refined prompting achieved the highest correctness scores.

---

## Main Findings

KG-RAG was useful when the original candidate list did not contain a specific concept that was supported by the segment.

It recovered specific missing concepts such as:

* `Reichenbach`
* `Birkenau`
* `Kristallnacht`
* `Bergen-Belsen`

However, the expanded candidate list also introduced more opportunities for weak, broad, or only incidentally related concepts.

The thesis therefore concludes that retrieval from the WO2 Thesaurus is best understood as a candidate-expansion and specificity-support method. It can improve specificity when relevant missing concepts are retrieved, but retrieval alone does not guarantee a more correct concept set.

---

## Folder Structure

```text
03_thesis_kg_rag/
│
├── data/
│   └── Local WO2Net-derived data files used for case selection and evaluation.
│       These files are not uploaded to GitHub for privacy reasons.
│
├── scripts/
│   ├── 01_parse_thesaurus.py
│   ├── 02_test_retrieval_on_examples.py
│   ├── 03_select_evaluation_segments.py
│   ├── 04_run_candidate_retrieval.py
│   ├── 05_build_kg_rag_prompts.py
│   ├── 06_validate_llm_outputs.py
│   ├── 07_summarize_kg_rag_outputs.py
│   ├── 08_build_refined_prompts.py
│   ├── 09_summarize_refined_outputs.py
│   ├── 10_build_baseline_prompts.py
│   ├── 11_summarize_baseline_outputs.py
│   ├── 12_create_method_comparison_table.py
│   ├── 13_create_expert_evaluation_tables.py
│   ├── 14_process_expert_evaluation.py
│   ├── retrieve_candidates.py
│   ├── kg_rag_prompts.py
│   ├── baseline_prompts.py
│   └── refined_prompts.py
│
└── results/
    ├── llm_prompts/
    │   ├── baseline/
    │   ├── refined/
    │   └── kg_rag/
    │
    └── expert_evaluation/
        └── responses_processed/
            └── Processed result summaries.
            These files may be kept local if they contain WO2Net-derived or expert-evaluation material.
```

---

## What Is Not Included

The scripts are included for transparency and to document the thesis workflow. However, private WO2Net-derived data and restricted project files are not included in the public repository.

Not included:

* raw `.vtt` interview files
* enriched segment files
* crowdsource validation data
* selected evaluation segment files
* generated prompts containing interview excerpts
* raw LLM outputs
* expert questionnaire responses
* consent-related material
* processed expert-evaluation files if they contain restricted material
* `models.py`, if it depends on WO2Net/project-restricted code or private data structures

The repository therefore documents the workflow, but it does not redistribute the underlying WO2Net data or restricted project files.

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

