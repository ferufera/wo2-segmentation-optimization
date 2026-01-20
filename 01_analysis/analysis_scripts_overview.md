# Analysis Scripts Overview

This document explains how the different analysis scripts in this repository fit together and what role each of them plays. The overall workflow moves from raw data handling, to analyzing individual user votes, and finally to making a consensus-based decision at the segment level.

In short, the pipeline follows this structure:

**Raw JSON files → Vote-level analysis → Segment-level consensus**

---

## 1. Data Consolidation (Helper Script)

**Script:** `consolidate_json_files.py`

This script is a utility script used to prepare the data for analysis. It reads the many small JSON files stored in the `enriched_segments/` and `validations/` folders and merges them into two larger files:

- `enriched_segments.json`
- `segment_validations.json`

The script does not perform any analysis by itself. Its main purpose is to make the later analysis steps more efficient, since working with a few consolidated files is much faster and cleaner than repeatedly loading thousands of small ones.

---

## 2. Vote-Level Analysis (Individual User Decisions)

The next two scripts analyze the data at the level of individual user votes. Each validation submitted by a user is treated as a separate data point. If multiple users reviewed the same segment, each of their votes is counted individually.

### 2.1 `initial_analysis.py`

This script performs a simple, first-pass analysis of the raw validation data. It loads the files directly and counts how often users selected actions such as **Edit** or **Remove**.

Key observations from this script include:
- Around **1250 total validations**, representing the total number of user submissions.
- A high number of **concept removals** and **start-time edits**.

These counts mainly show how much corrective work the crowd had to do and indicate that users were actively cleaning up the AI-generated output.

---

### 2.2 `analysis_crowdsource_mismatches.py`

This script builds on the initial analysis and uses the consolidated JSON files. It performs a more detailed analysis by looking at the content of segments and user comments, and by testing specific hypotheses.

Examples include checking whether start-time edits are associated with technical phrases such as *“intro”* or *“band loopt”*. The script also calculates overall acceptance and rejection patterns.

The results show a high non-acceptance rate, suggesting that a large portion of the AI-generated data required human correction. Concept assignment appears to be a major source of errors, and user comments often request more specific or accurate information.

---

## 3. Segment-Level Analysis (Consensus Decisions)

**Script:** `analysis_with_consensus.py`

This script aggregates individual user votes to make a final decision for each segment. Instead of counting votes, it determines whether a segment is **Accepted**, **Rejected**, or marked as **Conflict** based on a quorum threshold of 60%.

For example, if three users review a segment and two of them reject it, the segment is counted as rejected overall.

At this level:
- The total number of segments is lower than the number of votes, since multiple votes can apply to the same segment.
- Fewer start-time issues appear compared to the vote-level analysis, showing that several users often agreed on the same corrections.
- Most segments reach a clear consensus, with only a small fraction ending in conflict.

This script produces the final, consensus-based dataset that can be treated as ground truth.

---

## 4. Summary

- **Vote-level scripts** (`initial_analysis.py`, `analysis_crowdsource_mismatches.py`) focus on user effort, disagreement, and types of corrections.
- **Consensus-level analysis** (`analysis_with_consensus.py`) determines the final quality judgment per segment.

Overall, the workflow shows that users were highly active, that concept errors are the primary weakness of the AI output, and that the crowd generally agrees on whether a segment is acceptable or not.
