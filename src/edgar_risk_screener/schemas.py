"""Pydantic schemas for the risk screener.

NOTE (Option A redesign): RiskTopic / RiskTopicExtraction supported the
original whole-document synthesis approach (topic_extraction.py), which
produced different topic sets across repeated runs on the same filing
(see docs/architecture.md). They're superseded by paragraph_classifier.py
+ topic_aggregation.py, and kept below only for reference / backward
compatibility with any code that still imports them.
"""
from typing import List
from pydantic import BaseModel, Field


class RiskTopic(BaseModel):
    """Superseded by Option A -- see module docstring."""
    topic_name: str = Field(description="A short, normalized name for this risk topic, e.g. 'Supply chain disruption'")
    mention_count: int = Field(description="Approximate number of distinct passages discussing this topic in the text")
    summary: str = Field(description="One sentence describing how the filing frames this risk")
    source_quote: str = Field(description="A short (under 20 words) verbatim quote from the text supporting this topic")


class RiskTopicExtraction(BaseModel):
    """Superseded by Option A -- see module docstring."""
    topics: List[RiskTopic] = Field(description="All distinct risk topics found in the text")


class FlaggedTopic(BaseModel):
    """A category flagged as NEW or EXPANDED after the deterministic diff.

    example_paragraphs holds real classified paragraphs from the CURRENT
    year's filing that were labeled with this category -- not an
    LLM-picked quote. Since these are the actual paragraphs the count is
    built from, there's nothing separate to "verify": the evidence and
    the count share the same source, by construction. Capped (see
    screener.py) to keep the UI and payload readable, not because
    anything beyond the cap is less trustworthy.
    """
    topic_name: str
    status: str              # "NEW" or "EXPANDED"
    current_mentions: int
    prior_mentions: int
    example_paragraphs: List[str] = Field(default_factory=list)


class KPIChange(BaseModel):
    metric_name: str          # "Revenue", "GrossMarginPct", "NetIncome"
    current_value: float
    prior_value: float
    pct_change: float
    unusual: bool
