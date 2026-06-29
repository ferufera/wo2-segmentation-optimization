# KG-RAG Thesis Pipeline

This folder contains the thesis pipeline for testing whether the WO2 Thesaurus can improve LLM-based concept linking for Dutch Second World War oral history segments.

## Pipeline scripts

1. `01_parse_thesaurus.py`  
   Parses the WO2 Thesaurus RDF export into `data/thesaurus_concepts.csv`.

2. `02_test_retrieval_on_examples.py`  
   Tests the candidate retrieval logic on small debugging examples.

3. `03_select_evaluation_segments.py`  
   Creates a shortlist of real WO2Net segments from enriched segment data and crowd validation data.

4. `04_run_candidate_retrieval.py`  
   Retrieves WO2 Thesaurus candidate concepts for the selected real evaluation segments.

5. `05_build_kg_rag_prompts.py`  
   Builds KG-RAG concept selection prompts from segment text and retrieved candidates.

6. `06_validate_llm_outputs.py`  
   Cleans and validates manual LLM outputs and creates summary tables.

## Helper files

- `retrieve_candidates.py` contains the concept retrieval logic.
- `kg_rag_prompts.py` contains the KG-RAG prompt builder.

## Main comparison

The thesis compares three conditions:

1. Baseline prompting
2. Previously developed refined prompting
3. KG-RAG prompting

All conditions should be run with the same GPT model.