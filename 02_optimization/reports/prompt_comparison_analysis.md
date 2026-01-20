# Prompt Comparison Analysis

This document presents an analysis comparing the outputs generated using the **Original** prompt logic and the **Refined** prompt logic. The goal of this comparison is to evaluate whether the refined prompts successfully address the main issues identified during the crowd-based validation phase, particularly temporal drift and fragmented segment introductions.

The comparison is based on a batch analysis of **10 interview transcripts**. For each interview, the outputs from both prompt versions were aligned and evaluated using quantitative metrics related to segment start positions, segment length, and overall segmentation structure.

---

## Evaluation Method

For each interview, the outputs generated using the Original and Refined prompts were aligned caption-by-caption. A comparison script then computed quantitative metrics for each pair of outputs, including:

- **Start Index**, used to measure temporal drift caused by technical chatter  
- **Length of the first segment**, used to detect fragmented biographical introductions  
- **Number of segments and average segment length**, used to assess changes in segmentation structure  

In addition to aggregated observations, **per-interview comparison reports** were generated to verify that observed improvements were consistent across different interview styles and narrative structures.

---

## Removal of Technical Chatter

One of the main objectives of the prompt refinement was to reduce *temporal drift*. Temporal drift occurs when technical setup phrases (such as microphone checks or tape identification) are incorrectly treated as part of the narrative.

To evaluate this, the **Start Index** metric was used. This metric records the caption line at which the first segment begins. A higher start index in the refined output indicates that non-narrative introductory material was correctly skipped.

In **6 out of 10 interviews**, the refined prompt produced a later start index compared to the original output. For example:
- In `22_stiso_Zeehandelaar`, the first segment started **3 captions later**, indicating that the technical introduction was excluded.
- The same 3-caption shift was observed in `GV_DeJager_Huijsman`.
- Other interviews showed shifts of **2 captions**, reflecting a similar correction.

In the remaining **4 interviews**, no change in start index was observed. After manual inspection, these cases appeared correct, as the interviews began directly with narrative content and contained no technical chatter. In these cases, the refined prompt appropriately left the segmentation unchanged.

---

## Consolidation of Fragmented Introductions

Another issue identified during the analysis phase was the creation of very short initial segments containing only biographical information (e.g., the speaker’s name or date of birth). These segments were frequently rejected by crowd workers.

To assess whether this issue was reduced, the **Segment 1 Length** metric was used. This metric measures the number of caption lines in the first segment. An increase in this value suggests that short biographical fragments were merged into the main narrative segment.

Clear improvements were observed in several interviews:
- In `22_stiso_Zeehandelaar`, the first segment increased from **6 captions** in the original output to **37 captions** in the refined output.
- In `07_JKKV_Schelvis`, the first segment grew from **3 to 14 captions**, avoiding the creation of a very small introductory segment.
- A similar increase was observed in `GV_DeJager_vanderBlom`, where the first segment grew from **5 to 16 captions**.

When the original first segment was already sufficiently long, the refined prompt did not force a merge. For example, in `GV_DeJager_BroederFrans`, the first segment already contained **27 captions**, and its length remained unchanged. This suggests that the merging logic only applies when the initial segment falls below a reasonable narrative threshold.

---

## Cross-Interview Results Summary

The table below summarizes the main outcomes across all interviews included in the comparison:

| Interview ID                | Chatter Removed | Intro Merged | Start Index Shift |
|-----------------------------|-----------------|--------------|-------------------|
| 22_stiso_Zeehandelaar       | Yes             | Yes          | +3                |
| 07_JKKV_Schelvis            | Yes             | Yes          | +2                |
| GV_DeJager_Huijsman         | Yes             | Yes          | +3                |
| GV_DeJager_vanderBlom       | Yes             | Yes          | +1                |
| GV_DeJager_Drenth           | Yes             | No           | +2                |
| GV_DeJager_Schenk           | Yes             | No           | +2                |
| GV_NMKV_Sachsenhausen09     | Yes             | No           | +2                |
| GV_DeJager_BroederFrans     | No change       | No change    | 0                 |
| GV_DeJager_Ouwendijk        | No change       | No change    | 0                 |
| GV_DeJager_vanVliet         | No change       | No change    | 0                 |

This summary shows that improvements were consistent across multiple interviews, while neutral cases were preserved where no correction was necessary.

---

## Effects on Segmentation Structure and Coherence

Beyond addressing specific failure cases, the refined prompts also affected the overall segmentation structure.

In general, refined outputs tend to produce **larger and more coherent segments**, especially when the narrative develops gradually. For instance:
- In `GV_DeJager_Huijsman`, the number of segments decreased from **10 to 5**, while the average segment length increased from **64.3 to 126.6 captions**. This indicates a shift away from frequent splitting toward broader thematic grouping.

At the same time, the refined logic does not uniformly reduce segmentation granularity:
- In `GV_DeJager_Schenk`, the number of segments increased from **16 to 21**, suggesting that the refined prompts were able to identify distinct events more clearly when the interview content supported finer segmentation.

These results indicate that the refined prompts adapt segmentation behavior to the narrative structure rather than applying a single global strategy.

---

## Neutral and Failure Cases

Not all interviews showed measurable changes after prompt refinement. In several cases (e.g., `GV_DeJager_BroederFrans`, `GV_DeJager_Ouwendijk`, and `GV_DeJager_vanVliet`), no change in start index or introductory segment length was observed.

Manual inspection suggests that these interviews already began directly with narrative content and did not contain technical chatter or fragmented introductions. In these cases, the refined prompt correctly avoided unnecessary structural changes.

These neutral outcomes indicate that the refined logic is conservative rather than over-aggressive, applying corrections only when specific failure patterns are present.

---

## Summary

Overall, the comparison shows that the refined prompt logic successfully addresses the main causes of segment rejection identified earlier, particularly temporal drift caused by technical chatter and the fragmentation of biographical introductions.

These improvements were achieved without reducing segmentation quality. In several cases, the refined prompts produced clearer and more coherent narrative structure, while still allowing finer segmentation when appropriate. The results therefore suggest that the refined prompts represent a meaningful improvement over the original prompt logic.
