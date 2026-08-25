"""Track 2 Step 2 (Option A version): deterministic diff between two
years' category mention counts.

Simpler than the original design: since both years now report counts
against the EXACT SAME fixed category list (from paragraph-level
classification, not LLM-invented names), this is a plain dictionary
comparison. No fuzzy string matching (SequenceMatcher) needed -- that
was only necessary when topic names could drift between runs.
"""
from edgar_risk_screener.schemas import FlaggedTopic
from edgar_risk_screener.topic_aggregation import MAX_EXAMPLE_PARAGRAPHS

EXPANSION_MULTIPLIER = 2.0  # current mentions must be at least this many times prior mentions


def find_new_or_expanded_topics(
    prior_year_counts: dict[str, int],
    current_year_grouped: dict[str, list[str]],
) -> list[FlaggedTopic]:
    """current_year_grouped is {category: [paragraph_text, ...]} so real
    example paragraphs can be attached as evidence to each flagged topic.
    prior_year_counts only needs counts, since the prior year's
    paragraphs aren't shown in the UI (current-year evidence is what the
    analyst needs to act on).
    """
    flagged = []

    for category, current_paragraphs in current_year_grouped.items():
        current_count = len(current_paragraphs)
        prior_count = prior_year_counts.get(category, 0)

        if prior_count == 0:
            flagged.append(FlaggedTopic(
                topic_name=category,
                status="NEW",
                current_mentions=current_count,
                prior_mentions=0,
                example_paragraphs=current_paragraphs[:MAX_EXAMPLE_PARAGRAPHS],
            ))
        elif current_count >= EXPANSION_MULTIPLIER * prior_count:
            flagged.append(FlaggedTopic(
                topic_name=category,
                status="EXPANDED",
                current_mentions=current_count,
                prior_mentions=prior_count,
                example_paragraphs=current_paragraphs[:MAX_EXAMPLE_PARAGRAPHS],
            ))

    return flagged
