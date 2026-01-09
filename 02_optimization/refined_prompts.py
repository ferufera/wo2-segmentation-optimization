import json
from dataclasses import dataclass

# ==============================================================================
# IMPORT LOGIC
# 1. Try to import real models from the WO2Net package (for production use).
# 2. If that fails (e.g. IDE or standalone test), define compatible dummy classes.
# ==============================================================================
try:
    from models import Caption, Segment
except ImportError:
    @dataclass
    class Caption:
        start: float
        end: float  # Matches official model
        text: str

    @dataclass
    class Segment:
        start: float
        end: float
        text: str
        captions: list
        matched_concepts: list = None
        interviewee_name: str = "Ooggetuige"

# ==============================================================================
# PROMPT BUILDERS
# ==============================================================================

def _build_segment_prompt(captions: list[Caption], index_offset: int = 0, variation_suffix: str = "") -> str:
    """
    Creates a prompt for splitting an interview transcript into segments.
    Updated to handle 'Meta-Chatter' and 'Biographical Noise' issues.
    """

    captions_lines = []
    for i, c in enumerate(captions):
        global_index = i + index_offset
        start_formatted = f"{c.start:.2f}"
        text_line = c.text.replace("\n", " ").strip()
        captions_lines.append(f"[{global_index}][{start_formatted}s] {text_line}")

    captions_text_block = "\n".join(captions_lines)

    prompt = f"""

Below you will find a full transcript of an interview in Dutch with timestamps in seconds. 
Split this transcript into relevant segments according to the following strict rules:

Rule 1 (Definition): A segment is a coherent portion of an interview that focuses on questions related to one main topic or theme. It must be self-contained: it does not refer to content of a previous segment or need any information from other segments to be fully understood.

Rule 2 (Trimming Chatter): Set the start of a segment strictly when the interviewee begins their substantive narrative. Exclude the interviewer's setup questions (e.g., "State your name/birthdate") and procedural remarks (e.g., "Mic check", "Is the tape running?", "Snuift"). The segment should start with the answer, not the administrative setup.

Rule 3 (Merge Introductions): Do not create separate, short segments for biographical introductions (Name, Date of Birth, Place of Birth). If the start of the interview contains this info, merge it into the first substantive story segment so the introduction flows directly into the narrative.

Rule 4 (Topic Shift): A new segment begins only when there is a clear change of topic or a completely new question that shifts the focus. Follow‑up questions that stay on the same topic are part of the same segment.

Rule 5: Segments are between 1 minute and 5 minutes long.

Rule 6: There must be no overlap between segments and no captions left unassigned (unless they are purely administrative chatter excluded by Rule 2).

Rule 7: The output must always be a JSON list of objects, where each object contains:
- "caption_indices": the list of indices of the captions that belong to that segment.

Output format (strictly):

[
{{
    "caption_indices": [0,1,2,3]
}},
{{
    "caption_indices": [4,5,6,7,8]
}}
]

Do not give any introduction, explanation, comments or closing statements. Just valid JSON.

---

Here is the transcription with captions (index, starttime, text):

{captions_text_block}

{variation_suffix}

---

Return *only* the JSON output without any additional text or explanation. Do not include any text before or after the JSON.
""".strip()

    return prompt

def _build_segment_selector_prompt(segments: list) -> str:
    """
    Creates a strict rule-based prompt for selecting interview segments that are
    meaningful enough to be included in a dataset about World War II.
    """
    numbered_segments = []
    for i, segment in enumerate(segments):
        clean_text = segment.text.replace("\n", " ").strip()
        numbered_segments.append(f"[{i}] {clean_text}")

    segment_block = "\n\n".join(numbered_segments)

    prompt = f"""
You are given several text segments from an interview. 
Each segment is shown with an index in square brackets, for example [0].

Select only those segments that are meaningful and relevant to **World War II**,
strictly following these rules:

Rule 1: A segment must contain substantial content directly related to World War II:
  - events, historical situations
  - organizations, groups, or locations
  - personal experiences, eyewitness accounts
  - names of relevant people or places

Rule 2: The topic related to World War II must be explicitly mentioned or clearly
the main focus of the segment. Segments where the connection to World War II
is vague or only implied must be excluded.

Rule 3: A segment must be self-contained and make sense on its own without needing information from other segments.

Rule 4: Exclude segments that:
  - only mention the topic without adding new or informative content
  - only consist of short answers like “I don’t remember” or vague statements
  - consist only of a question without any meaningful explanation or answer

Rule 5: Do not select segments that are mostly meta-discussion (about the interview itself) or administrative details.

Rule 6: Include a segment only if it clearly contributes new, concrete, or detailed information about World War II.

Possible outcomes:
- None of the segments are relevant
- Some of the segments are relevant
- All of the segments are relevant

Output format:
Return a valid JSON object in this format:

{{
  "relevant_segments": [0, 2, 5, 6]
}}

Do not add any explanations, commentary, or text outside of the JSON.

---

Segments:
{segment_block}
""".strip()

    return prompt

def _build_match_validation_prompt(segment_text: str, concepts: list[str]) -> str:
    """
    Builds a strict prompt for an LLM to validate which concepts are truly relevant
    to a given interview segment, and to assign a confidence score.
    """
    concept_list = "\n".join([f"- {c}" for c in concepts])

    prompt = f"""
Below is a fragment from an oral history interview about World War II:

\"\"\"{segment_text}\"\"\"

Below that is a list of concepts from a World War II thesaurus.
Your task is to validate which concepts are clearly relevant to the fragment.

Follow these strict rules:

Rule 1: Only select a concept if the fragment is clearly about that topic.
Rule 2: Do NOT select a concept based on a single incidental word match; it must be central to the fragment.
Rule 3: If a specific event, place, or organization is mentioned, select the concept only if it is unquestionably referring to that concept.
Rule 4: If there is some relevance but you are unsure, you may include the concept with a lower score.
Rule 5: For each validated concept, include a confidence score between 0 and 1 (1.0 = very certain, 0 = very uncertain).

Output must be strictly in this JSON format and nothing else:

[
  {{
    "concept": "Concept name",
    "score": 0.85
  }},
  {{
    "concept": "Another concept",
    "score": 0.65
  }}
]

Concept list:
{concept_list}

Important:
- Output ONLY the JSON list, with no explanations, no extra text, and no additional fields.
""".strip()

    return prompt

def _build_topdown_matching_prompt(concept_labels: list[str], segment_text: str) -> str:
    """
    Builds a strict LLM prompt to match WWII thesaurus concepts to an interview segment.
    Updated to handle 'Specificity' issues (User Preference for Named Entities).
    """
    concept_list = "\n".join([f"- {label}" for label in concept_labels])

    prompt = f"""
Below is a fragment from an oral history interview about World War II:

\"\"\"{segment_text}\"\"\"

Below that is a list of controlled vocabulary concepts from a World War II thesaurus.

Your task:
- Identify ALL and ONLY the concepts from the list that represent the **main topics** of this fragment.
- Ignore side remarks, digressions or incidental mentions that are not central to the segment.
- For each selected concept, assign a confidence score between 0 and 1 (1.0 = very certain).
- Use only the concepts exactly as listed. Do not invent or modify concept names.

Rules:
1. **Prioritize Specificity**: If the fragment mentions a specific Named Entity (e.g., a specific camp like 'Westerbork' or 'Reichenbach', or a specific location/person) that appears in the list, you MUST select it. This is more important than generic themes.

2. **Avoid Generic Tagging**: Only include broad themes (e.g., "Transport", "Oorlogsgetroffenen", "Familieleven") if the segment discusses the *process* or *experience* of that theme in detail. 
   - Example: If someone says "We went to Reichenbach", select "Reichenbach". Do NOT select "Transport" unless they describe the train ride itself.

3. **Contextual Relevance**: Select a concept only if it represents a **key theme** of the fragment as a whole. Do NOT select a concept just because a word appears (e.g., mentioning a Bible does not make 'Religion' relevant unless they discuss faith).

4. If the fragment describes a specific example or event that falls under a broader concept,
   include that broader concept only if Rule 2 is satisfied.

5. Do NOT include any concept with a score of 0.5 or lower.
6. Multiple concepts can be selected.
7. Never return concepts that are not present in the list.

Output format (JSON only, no explanations):

[
  {{
    "concept": "Jodenvervolging",
    "score": 0.92
  }},
  {{
    "concept": "Deportaties",
    "score": 0.81
  }}
]

Concept list:
{concept_list}
    
Important:
- Return ONLY a JSON list as shown, with no explanations, no extra text, and no other fields.
""".strip()

    return prompt

def _build_extract_name_prompt(captions: list[Caption]) -> str:
    """
    Creates a prompt for extracting the name of the interviewee from an interview transcript.
    """
    captions_lines = []
    for i, c in enumerate(captions):
        global_index = i 
        start_formatted = f"{c.start:.2f}"
        text_line = c.text.replace("\n", " ").strip()
        captions_lines.append(f"[{global_index}][{start_formatted}s] {text_line}")

    captions_text_block = "\n".join(captions_lines)

    prompt = f"""

Below you will find a transcript of the first 5 minutes of an interview in Dutch with timestamps in seconds. 

Your job is to extract the full name of the interviewee from the transcript. 

Do not give any introduction, explanation, comments or closing statements. Just valid JSON in the following format:

[
  {{
    "name": "Jan Jansen"
  }}
]

---

Here is the transcription with captions (index, starttime, text):

{captions_text_block}

---

Return *only* the JSON output without any additional text or explanation. Do not include any text before or after the JSON.
""".strip()
    return prompt

def _build_segment_title_prompt(segment: dict) -> str:
    """
    Builds a prompt to generate a short title for a segment.
    Updated to reduce generic titles ('Oorlog') and encourage specificity ('Arrestatie in Rotterdam').
    """
    name = segment.get("interviewee_name", "Ooggetuige")
    text = segment.get("text", "")
    concepts = ", ".join([c["name"] for c in segment.get("matched_concepts", [])])

    return f"""
Your task is to create a short, neutral, and informative Dutch title (maximum 15 words)
for the following interview segment from a Dutch World War II oral history collection.

Rules:
- The title must always start with: "{name} vertelt over ..."
- Summarize the **specific core topic** of the segment (not just a broad theme).
- **Be Specific**: Include specific locations, events, or family members if they are central to the story.
  - Bad: "{name} vertelt over de oorlog" (Too generic)
  - Bad: "{name} vertelt over zijn familie" (Too generic)
  - Good: "{name} vertelt over de arrestatie van zijn vader in Amsterdam"
- Select the topic using your own judgement and, if relevant, the Key concepts provided.
- The title must be in Dutch.
- Output strictly valid JSON in this exact format (no code block markers, no explanations):
{{"title": "Jan Jansen vertelt over de Razzia van Rotterdam"}}

Input:
Interviewee: {name}
Transcript text: {text}
Key concepts: {concepts}

Only return the JSON, without explanations or extra text.
""".strip()