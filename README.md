# WO2Net Segmentation Optimization Workbench

This repository contains an optimization workbench for the WO2Net oral history pipeline. It documents the analysis of segmentation errors, especially the 66% rejection rate found in crowdsourced validation data, and implements refined prompt logic to improve title specificity, start-time precision, fragment handling, and concept matching.

The repository was later extended with an independent bachelor thesis component on concept linking. This thesis work evaluates whether retrieval from the WO2 Thesaurus can improve the correctness and specificity of LLM-based concept linking for selected WO2Net oral history segments.

For transparency, the repository contains two connected but distinct parts:

1. **Segmentation optimization and prompt refinement**
   Original Group 1 work on diagnosing validation problems and improving the WO2Net segmentation/prompting workflow.(Part of the Digital Humanities & Social Analytics in Practice Course)

2. **Bachelor thesis extension: KG-RAG for concept linking**
   Independent thesis work by Feruza Bakhtiyorova on thesaurus-based retrieval for improving concept specificity in LLM-based concept linking.

---

## Bachelor Thesis Extension

The folder `03_thesis_kg_rag/` contains the independent bachelor thesis pipeline for testing KG-RAG concept linking with the WO2 Thesaurus.

For details on the numbered scripts, helper files, workflow, and privacy restrictions, see:

`03_thesis_kg_rag/README.md`

---

## Project Objective

The original goal of this project was to reduce the high rejection rate observed in crowdsourced validations of AI-generated interview segments. The repository served as a research lab to diagnose errors in the production pipeline and engineer specific prompt-based solutions.

The later thesis extension focuses on a related but narrower problem: whether retrieval from the WO2 Thesaurus can help an LLM select more specific and historically appropriate concepts for oral history segments.

---

# Part 1: Segmentation Optimization and Prompt Refinement

## Phase 1: The Baseline

We analysed a dataset of 1,250 crowdsourced validations to establish a baseline for the current pipeline's performance.

### The Problem

* **Total validations:** 1,250
* **Rejection rate:** 66.0%
* **Rejected or heavily edited segments:** 825
* **Consensus status:** 373 segments were outright rejected by voting consensus

The high rejection rate suggested that the AI-generated segmentation and enrichment workflow needed closer diagnosis. The aim was not only to count rejected segments, but also to understand why validators rejected or edited them.

---

## Root Cause Analysis

Using the diagnostic scripts in the `01_analysis/` folder, we identified four primary failure modes.

### 1. Concept Errors

* **261 cases**
* Validators often rejected generic concepts in favour of more specific named entities.
* Example pattern: a broad concept such as `Transport` was less useful than a more specific concept such as `Westerbork` when the segment supported the specific entity.

### 2. Title Edits

* **140 cases**
* Validators often edited or rejected generic titles.
* Example pattern: generic titles such as `Vertelt over de oorlog` were less useful than specific titles referring to locations, events, or experiences, such as `Arrestatie in Rotterdam`.

### 3. Temporal Drifts

* **78 cases**
* Segments frequently started too early.
* Some segments included technical setup or recording chatter such as `Band loopt` or microphone checks before the actual substantive interview content began.

### 4. Fragment Removal

* **45 cases**
* Short segments containing only biographical introductions, such as name or birthdate, were often marked as irrelevant.
* These fragments were usually more useful when merged into the first substantive narrative segment rather than treated as standalone segments.

---

## Phase 2: The Solution: Prompt Engineering

Based on the analysis, refined prompt logic was developed in `02_optimization/`. The main implementation is located in `refined_prompts.py`.

The refined prompt logic implements four specific fixes.

### 1. Anti-Chatter

The prompt explicitly instructs the model to ignore technical setup phrases such as:

* `Band loopt`
* microphone checks
* other recording setup text

This was designed to reduce temporal drift and prevent segments from starting before the substantive interview content.

### 2. Merge Introductions

The prompt forces the model to merge short biographical introductions into the first substantive narrative segment. This prevents short name/birthdate fragments from being treated as independent meaningful segments.

### 3. Title Specificity

The prompt constraints were updated to avoid generic templates and enforce more specific titles.

The refined title logic encourages titles that:

* refer to specific locations, events, or experiences
* avoid generic formulations
* stay within a concise title length

### 4. Concept Specificity

The concept-matching logic was revised to prioritize specific named entities over broad ontological themes when the segment supports them.

This was intended to reduce overly generic concept links and make the output more useful for search and archival exploration.

---

## Segmentation Optimization Repository Structure

```text
wo2-segmentation-optimization/
│
├── 01_analysis/
│   ├── scripts/
│   │   └── Python scripts used to calculate rejection rates and diagnose validation problems.
│   │
│   ├── reports/
│   │   └── Text files containing evidence, statistics, and diagnostic summaries.
│   │
│   └── analysis_scripts_overview.md
│       └── Overview of the analysis pipeline and how the scripts connect,
│           from raw votes to consensus decisions.
│
├── 02_optimization/
│   ├── reports/
│   │   └── prompt_comparison_analysis.md
│   │       └── Analysis comparing original and refined prompt outputs.
│   │
│   ├── models.py
│   │   └── Data structures such as Caption and Segment from WO2Net.
│   │       This file may not be included on GitHub due to privacy or project restrictions.
│   │
│   ├── refined_prompts.py
│   │   └── The optimized prompt logic.
│   │
│   ├── process_vtt_batch.py
│   │   └── Script that runs the refined prompt logic on VTT interview data.
│   │
│   ├── compare_results.py
│   │   └── Script to compare original and refined outputs.
│   │
│   └── original_prompts_archive.py
│       └── Archive of the old prompt logic for comparison.
│           This file may not be included on GitHub due to privacy or project restrictions.
│
├── 03_thesis_kg_rag/
│   └── Independent bachelor thesis extension for KG-RAG concept linking.
│       See 03_thesis_kg_rag/README.md for details.
│
├── data/
│   ├── vtt_files/
│   │   └── Raw .vtt interview files.
│   │       These files are not uploaded to GitHub for privacy reasons.
│   │
│   └── crowdsource_data/
│       ├── enriched_segments.json
│       └── segment_validations.json
│       These files are not uploaded to GitHub for privacy reasons.
│
└── results/
    ├── ready_prompts/
    ├── json_outputs/
    └── analysis_reports/
    These generated outputs are not uploaded to GitHub if they contain restricted material.
```

---

## Usage: Segmentation Optimization Workflow

To generate new optimized prompts using the refined logic:

### 1. Prepare data

Place your `.vtt` interview files into:

```text
data/vtt_files/
```

### 2. Run the batch processor

Open your terminal in the main project folder and run:

```bash
python 02_optimization/process_vtt_batch.py
```

### 3. View results

The script parses the interviews, applies the refined prompt rules, and saves the resulting prompt files in:

```text
results/ready_prompts/
```

---

# Part 2: Bachelor Thesis Extension: KG-RAG for Concept Linking

## Thesis Title

**Improving Concept Specificity in LLM-Based Concept Linking for Oral History Segments Using the WO2 Thesaurus**

This part of the repository was developed independently by **Feruza Bakhtiyorova** as a Bachelor Artificial Intelligence thesis at Vrije Universiteit Amsterdam.

This thesis work builds on the earlier segmentation and prompt-refinement project, but it is a separate research component. It focuses specifically on the concept-linking stage and was not co-authored by Dunya Boon.

---

## Thesis Objective

The thesis evaluates whether retrieval from the WO2 Thesaurus improves LLM-based concept linking for WO2Net oral history segments.

The central research question is:

> To what extent does retrieval from the WO2 Thesaurus improve the correctness and specificity of LLM-based concept linking for oral history segments?

The thesis does not attempt to solve oral history interpretation as a whole. It tests a narrower methodological question: whether adding a thesaurus retrieval step helps the model recover more specific concepts that may be missing from the original candidate list.

---

## Thesis Method

The thesis compares three concept-linking conditions on the same five selected WO2Net oral history segments:

1. **Baseline prompting**
   Uses the original candidate concepts from the previous WO2 oral history matching pipeline and applies the archived baseline prompt logic.

2. **Refined prompting**
   Uses the same original candidate concepts, but applies stricter prompt logic from earlier prompt-refinement work.

3. **KG-RAG prompting**
   Retrieves additional candidate concepts from the WO2 Thesaurus before LLM-based concept selection.

All three conditions used the same LLM, GPT-5.5 Instant. This means the comparison focuses on the method setup rather than model choice.

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

### Aggregate expert-rating results

| Condition | Expert ratings | Unique concept rows | Strict correct rate | Partial-credit correctness | Appropriate specificity, all ratings | Appropriate specificity, applicable only |
| --------- | -------------: | ------------------: | ------------------: | -------------------------: | -----------------------------------: | ---------------------------------------: |
| Baseline  |            115 |                  23 |              66.96% |                     75.23% |                               54.78% |                                   65.62% |
| Refined   |             95 |                  19 |              68.42% |                     77.47% |                               61.05% |                                   74.36% |
| KG-RAG    |            160 |                  32 |              65.62% |                     74.68% |                               59.38% |                                   79.17% |

KG-RAG achieved the highest applicable-specificity rate, meaning that experts more often judged its concepts to be at the right level of detail when specificity was applicable. However, refined prompting achieved the highest correctness scores.

---

## Main Thesis Findings

KG-RAG was useful when the original candidate list did not contain a specific concept that was supported by the segment.

It recovered specific missing concepts such as:

* `Reichenbach`
* `Birkenau`
* `Kristallnacht`
* `Bergen-Belsen`

However, the expanded candidate list also introduced more opportunities for weak, broad, or only incidentally related concepts.

The thesis therefore concludes that retrieval from the WO2 Thesaurus is best understood as a candidate-expansion and specificity-support method. It can improve specificity when relevant missing concepts are retrieved, but retrieval alone does not guarantee a more correct concept set.

---

# Transparency and Research Ethics

This repository contains work from different stages of a research process. For ethical and transparent reporting, the contributions are separated clearly.

## Group 1 work

The original segmentation optimization and prompt-refinement work was developed as Group 1 work.

* **Feruza Bakhtiyorova**
  Data preparation, rejection analysis, prompt engineering, repository setup, and methodology.

* **Dunya Boon**
  Visualization of results, literature research, and academic reporting.

## Independent thesis work

The bachelor thesis extension in `03_thesis_kg_rag/` was developed independently by:

* **Feruza Bakhtiyorova**
  Research design, KG-RAG implementation, case selection, prompt generation, expert evaluation processing, result analysis, and thesis writing.

The thesis extension uses the earlier work as background and methodological context, but the KG-RAG implementation, expert evaluation processing, result analysis, and thesis writing were conducted independently by Feruza Bakhtiyorova.

---

# Data Availability and Privacy Notes

The WO2Net interview data, validation data, enriched segment files, expert evaluation responses, and related processed data are **not included in this repository** because they may contain sensitive, restricted, or non-public research material.

For privacy and ethical research reasons, the following files and folders are kept local and are not uploaded to GitHub:

* raw `.vtt` interview files
* WO2Net enriched segment files
* crowdsource validation data
* selected evaluation segment files derived from WO2Net data
* expert questionnaire responses
* consent-related material
* intermediate files containing interview excerpts or concept validation information
* generated prompts containing interview excerpts
* raw LLM outputs if they contain segment text or restricted source material
* processed expert-evaluation files if they contain restricted material

The repository therefore documents the research workflow, scripts, prompt logic, and reproducibility structure, but it does not redistribute the underlying WO2Net data.

Where possible, public external resources are linked, such as the WO2 oral history matching pipeline, the public subtitle repository, the WO2 Thesaurus dataset, and the SPARQL endpoint. However, any local WO2Net-derived data used during the thesis remains private and must be obtained or accessed only through the appropriate project permissions.

---

# Related Resources

* WO2 oral history matching pipeline:
  https://github.com/Oorlogsbronnen/wo2-oral-history-matching-pipeline

* Raw subtitle files:
  https://github.com/Oorlogsbronnen/segmenten_ondertiteling

* WO2 Thesaurus dataset:
  https://data.spinque.com/ld/data/oorlogsbronnen/wo2_thesaurus/

* WO2 Oorlogsbronnen SPARQL endpoint:
  https://query.ldmax.nl/wo2-oorlogsbronnen/nfeAGR

