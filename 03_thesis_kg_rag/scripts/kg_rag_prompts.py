"""
kg_rag_prompts.py

This file contains the prompt builder functions for the thesis KG-RAG pipeline.

It builds LLM prompts from retrieved WO2 Thesaurus candidate concepts.

Pipeline position:
    segment text
        -> candidate retrieval from WO2 Thesaurus
        -> this prompt builder
        -> LLM concept selection
        -> structured JSON output

Important:
    This file does not call the LLM. It only builds prompt strings.

    The prompt must not include validation comments, consensus status, removed
    concepts, missing-concept comments, or human evaluation notes. Those fields
    are part of the evaluation data and should not be shown to the model.
"""


def _format_candidate_concepts(candidates: list[dict]) -> str:
    """
    Format retrieved WO2 Thesaurus candidates for the prompt.

    I include the label and URI because the model must choose exact concepts
    from the candidate list.

    I include concept types only as lightweight context.

    I intentionally do NOT include retrieval score, retrieval source, or
    retrieval reason in the LLM prompt. Those fields are useful for inspection
    and transparency, but showing them to the LLM may bias the selection.
    """
    if not candidates:
        return "No candidate concepts were retrieved."

    lines = []

    for index, candidate in enumerate(candidates, start=1):
        label = candidate.get("label", "")
        uri = candidate.get("uri", "")
        types = " | ".join(candidate.get("types", []))

        lines.append(
            f"{index}. Label: {label}\n"
            f"   URI: {uri}\n"
            f"   Types: {types}"
        )

    return "\n\n".join(lines)


def _build_kg_rag_concept_selection_prompt(
    segment_id: str,
    segment_text: str,
    candidates: list[dict]
) -> str:
    """
    Build a KG-RAG concept selection prompt for one oral history segment.

    Main goal:
        Ask the LLM to select only those retrieved concepts that are actually
        supported by the segment.

    The candidate list comes from the WO2 Thesaurus retrieval step. The model
    may only choose from this list and may not invent new URIs.
    """
    candidate_block = _format_candidate_concepts(candidates)

    prompt = f"""
Below is a fragment from a Dutch oral history interview about the Second World War.

Segment ID:
{segment_id}

Segment text:
\"\"\"{segment_text}\"\"\"

Below is a list of candidate concepts retrieved from the WO2 Thesaurus.

Your task:
Select ALL and ONLY the candidate concepts that are clearly supported by the segment.

Rules:
1. Use only labels and URIs from the candidate list.
2. Do not invent new concepts or new URIs.
3. Select a concept only if the segment is clearly about that topic.
4. Do not select a concept based only on a single incidental word match.
5. Do not select a concept only because it is generally related to the Second World War.
6. Prefer specific concepts when they are clearly supported by the segment.
7. Do not select concepts that are too narrow if the segment does not clearly support that level of specificity.
8. If both a broad and a specific concept are available, select the specific concept only when the text supports it.
9. If a candidate is a technical metadata label, such as fixedDateEvent or intervalEvent, reject it unless the segment is explicitly about that technical category.
10. If a candidate is a personal event, such as Geboren, Overleden, Omgekomen, or Ondergedoken, select it only if that personal event is central to the segment.
11. If none of the candidates are clearly supported, return an empty selected_concepts list.
12. For every selected concept, include a short evidence quote from the segment.
13. The "uri" field must contain the plain URI string only.
14. Do not format URIs as Markdown links.
15. Do not use markdown anywhere in the output.

Candidate concepts:
{candidate_block}

Output format:
Return only valid JSON in this exact format:

{{
  "segment_id": "{segment_id}",
  "selected_concepts": [
    {{
      "uri": "https://data.niod.nl/WO2_Thesaurus/example",
      "label": "label from candidate list",
      "confidence": 0.85,
      "evidence": "short quote from the segment",
      "reason": "brief reason why this concept is supported"
    }}
  ],
  "rejected_candidates": [
    {{
      "uri": "https://data.niod.nl/WO2_Thesaurus/example",
      "label": "candidate label",
      "reason": "brief reason why this candidate was not selected"
    }}
  ],
  "missing_candidate_suggestions": [
    {{
      "label_or_keyword": "possible missing concept or keyword",
      "reason": "why it might be relevant but was not available in the candidate list"
    }}
  ]
}}

Important:
- Return ONLY JSON.
- Do not include explanations outside the JSON.
- Do not use markdown.
- Do not add code block markers.
- URI values must be plain URL strings, for example:
  "https://data.niod.nl/WO2_Thesaurus/events/4354"
- URI values must NOT look like:
  "[https://data.niod.nl/...](https://data.niod.nl/...)"
""".strip()

    return prompt