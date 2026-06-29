"""
models.py

This file contains lightweight data model definitions used by the prompt
builder functions copied from the previous WO2Net optimization work.

In the bachelor thesis pipeline, this file is included mainly to support
imports in:

    refined_prompts.py

Pipeline role:
    supporting module for prompt generation

Important:
    The thesis experiment does not directly focus on these model classes.
    They are kept here so that the copied refined prompt builder can run inside
    the self-contained thesis folder without depending on files from the earlier
    02_optimization folder.
"""

from dataclasses import dataclass
from typing import Optional

__all__ = [
    "Caption",
    "Segment",
    "ThesaurusConcept",
    "EnrichedSegment",
]

@dataclass
class Caption:
    start: float
    end: float
    text: str

@dataclass
class Segment:
    start: float
    end: float
    text: str
    captions: list[Caption]

@dataclass
class ThesaurusConcept:
    uri: str
    name: str
    category: str
    alternate_names: Optional[list[str]]
    description: Optional[str]
    top_concept: list[str]
    narrower: list[str]

@dataclass
class MatchedConcept:
    concept: ThesaurusConcept
    source: Optional[str]
    score: Optional[float]

@dataclass
class EnrichedSegment:
    segment: Segment
    matched_concepts: list[MatchedConcept]