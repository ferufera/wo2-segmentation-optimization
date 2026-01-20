# WO2Net Segmentation Optimization Workbench

This repository contains an optimization workbench for the WO2Net oral history pipeline. It documents the analysis of segmentation errors (specifically the 66% rejection rate) and implements refined prompt logic to fix issues with title specificity, start-time precision, and concept matching.

## Project Objective

The goal of this project is to reduce the high rejection rate observed in crowdsourced validations of AI-generated interview segments. This repository serves as a research lab to diagnose errors in the production pipeline and engineer specific prompt-based solutions.

## Phase 1: The Baseline (Initial State)

We analyzed a dataset of 1,250 crowdsourced validations to establish a baseline for the current pipeline's performance.

### The Problem
* Total Validations: 1,250
* Rejection Rate: 66.0% (825 segments rejected or heavily edited)
* Consensus Status: 373 segments were outright rejected by voting consensus.

### Root Cause Analysis
Using the diagnostic scripts in the analysis folder, we identified four primary failure modes:

1.  **Concept Errors (261 cases):** Users rejected generic concepts (like "Transport") in favor of specific named entities (like "Westerbork").
2.  **Title Edits (140 cases):** Users rejected generic titles ("Vertelt over de oorlog") and requested specific locations or events ("Arrestatie in Rotterdam").
3.  **Temporal Drifts (78 cases):** Segments frequently started too early, capturing technical chatter ("Band loopt", "Mic check").
4.  **Fragment Removal (45 cases):** Short segments containing only biographical intros (Name/Birthdate) were marked as irrelevant.

## Phase 2: The Solution (Prompt Engineering)

Based on the analysis, we developed `refined_prompts.py` (located in the optimization folder) to implement four specific fixes:

1.  **Anti-Chatter:** Explicitly instructs the model to ignore technical setup phrases ("Band loopt") to fix temporal drift.
2.  **Merge Intros:** Forces the model to merge biographical introductions into the first substantive narrative segment.
3.  **Title Specificity:** Updated prompt constraints to forbid generic templates and enforce a 15-word limit, focusing on specific events.
4.  **Concept Specificity:** Revised matching logic to prioritize Specific Named Entities over broad ontological themes.

## Repository Structure

* `wo2-segmentation-optimization/`
    * `01_analysis/`
        * `scripts/` - Python scripts used to calculate the rejection rates
        * `reports/` - Text files containing the evidence and stats
        * `analysis_scripts_overview.md` - Overview of the analysis pipeline and how the scripts connect, from raw votes to consensus decisions
    * `02_optimization/` - **Main Processing Engine**
        * `reports/`
            * `prompt_comparison_analysis.md` - Analysis comparing original vs refined prompt outputs
        * `models.py` - Data structures (Caption, Segment) from WO2Net (not on GitHub due to privacy reasons)
        * `refined_prompts.py` - The optimized prompt logic (The Solution)
        * `process_vtt_batch.py` - The script that runs the prompts on your data
        * `compare_results.py` - Script to compare Original vs Refined outputs
        * `original_prompts_archive.py` - Archive of the old logic for comparison (not on GitHub due to privacy reasons)
    * `data/` - Input Data (Not on GitHub)
        * `vtt_files/` - Place your raw .vtt interview files here
        * `crowdsource_data/` - Combined Enriched Segments and Validations
            * `enriched_segments.json` - Aggregated from original individual enriched segment files
            * `segment_validations.json` - Aggregated from original individual validation files
    * `results/` - Output Data (Not on GitHub)
        * `ready_prompts/` - The script saves the generated prompt files here
        * `json_outputs/` - Raw JSON outputs from ChatGPT (Input for comparison)
        * `analysis_reports/` - Generated reports comparing performance

## Usage

To generate new, optimized prompts using the refined logic, follow these steps:

1.  **Prepare Data**
    Place your `.vtt` interview files into the `data/vtt_files/` folder.

2.  **Run the Batch Processor**
    Open your terminal in the main project folder and run the processing script located in the optimization folder:

    python 02_optimization/process_vtt_batch.py

3.  **View Results**
    The script will parse the interviews, apply the new prompt rules, and save the resulting text files in `results/ready_prompts/`.

## Authors - Group 1

* **Feruza Bakhtiyorova (Artificial Intelligence)** - Data preparation, rejection analysis, prompt engineering, repository setup, and methodology (in the process).
* **Dunya Boon (Communication)** - Visualization of results, literature research, and academic reporting (upcoming).
