"""Grounding check: confirms a flagged topic's cited quote actually appears
in the source text, before the analyst is asked to trust it.

Same "don't silently trust unverified LLM output" principle as
edgar_10k_research_agent's segment validator, applied to text instead of
numbers. This confirms the quote is grounded, NOT that the topic itself is
correct or complete -- see architecture.md limitation #3.
"""
from edgar_risk_screener.schemas import FlaggedTopic


def verify_quote(quote: str, source_text: str) -> bool:
    return quote.strip() in source_text


def verify_flagged_topics(
    flagged_topics: list[FlaggedTopic],
    current_year_text: str,
    prior_year_text: str = "",
) -> list[FlaggedTopic]:
    """Return a new list with quote_verified/prior_quote_verified set correctly for each topic."""
    updated = []
    for topic in flagged_topics:
        update = {"quote_verified": verify_quote(topic.source_quote, current_year_text)}
        if topic.prior_source_quote is not None:
            update["prior_quote_verified"] = verify_quote(topic.prior_source_quote, prior_year_text)
        updated.append(topic.model_copy(update=update))
    return updated
