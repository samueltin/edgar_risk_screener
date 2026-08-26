"""Pydantic schemas for the risk screener.

Track 2 (paragraph-level classification into a fixed taxonomy) has been
fully removed, along with its schemas (RiskTopic, RiskTopicExtraction,
FlaggedTopic). Only Track 1 (KPIChange) and Track 3 (SubTopicChange)
remain.
"""
from typing import List
from pydantic import BaseModel, Field


class SubTopicChange(BaseModel):
    """A change detected via native sub-topic extraction (see
    subtopic_extraction.py / subtopic_diff.py), the company's OWN heading
    structure.

    status is "NEW" (heading has no good match in the prior year),
    "REMOVED" (a prior-year heading has no good match this year), or
    "UPDATED" (heading matched an existing prior-year topic, but an LLM
    comparison of the two years' body text for that SAME topic found
    content genuinely new this year -- new_points holds what it found).

    A matched topic with nothing new is not reported as a change at all
    -- UPDATED only appears when there's something to show.

    prior_full_text and current_full_text hold the REAL, complete body
    text for both years (only populated for UPDATED, since that's the
    only status where both years' text exists for the same topic) --
    added so the analyst can verify each new_points claim directly
    against the real source text side by side, rather than trusting the
    LLM's summary alone. This is genuine, freshly-fetched filing text
    displayed by the running app for the user's own analysis, not static
    content embedded in code.
    """
    heading: str
    status: str              # "NEW", "REMOVED", or "UPDATED"
    body_preview: str = ""   # first ~300 chars of the heading's body text, for context (NEW/REMOVED)
    new_points: List[str] = Field(default_factory=list)  # only populated for status="UPDATED"
    prior_full_text: str = ""    # full prior-year body text, only populated for status="UPDATED"
    current_full_text: str = ""  # full current-year body text, only populated for status="UPDATED"


class KPIChange(BaseModel):
    metric_name: str          # "Revenue", "GrossMarginPct", "NetIncome"
    current_value: float
    prior_value: float
    pct_change: float
    unusual: bool
