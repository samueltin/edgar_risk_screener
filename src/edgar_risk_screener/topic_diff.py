"""Track 2 Step 2: deterministic diff between two years' risk topic lists.

No LLM here. Given the topics extracted for each year separately (via
topic_extraction.py), this module decides which are NEW or EXPANDED using
a fixed, auditable rule.

Topics in a fixed taxonomy category (see schemas.RiskCategory) are matched
by exact category equality -- deterministic, immune to LLM naming drift.
Topics in the "Emerging or unanticipated risk" bucket still have
LLM-invented free-text names (that's the point -- it's the escape hatch for
a risk that doesn't fit any fixed category), so those are matched by string
similarity as before. See docs/architecture.md limitation #2: this fuzzy
matching is now scoped to just that bucket, but is still a known
simplification there.

A topic backed by only a single mention is marked low_confidence rather
than filtered out. Measured empirically (3 runs of the same MSFT filing):
every category that flickered in/out between runs had mention_count == 1
in every run it appeared -- thin, incidental single-sentence mentions are
where the LLM's judgment call ("is this worth its own topic entry?") is
least stable. Filtering these out would risk silently hiding a genuinely
new risk that's only mentioned once so far, which is exactly the early,
quiet signal Track 2B exists to catch -- so they're still surfaced, just
flagged as needing more scrutiny before trusting them.
"""
from difflib import SequenceMatcher
from edgar_risk_screener.schemas import RiskTopic, FlaggedTopic, EMERGING_CATEGORY

SIMILARITY_THRESHOLD = 0.6   # emerging-bucket topic names at least this similar count as "the same" topic
EXPANSION_MULTIPLIER = 2.0   # current mentions must be at least this many times prior mentions
LOW_CONFIDENCE_MENTION_THRESHOLD = 1   # a topic backed by this many mentions (or fewer) is flagged low_confidence


def find_new_or_expanded_topics(
    prior_year_topics: list[RiskTopic],
    current_year_topics: list[RiskTopic],
) -> list[FlaggedTopic]:
    flagged = []

    for current in current_year_topics:
        if current.category == EMERGING_CATEGORY:
            candidates = [t for t in prior_year_topics if t.category == EMERGING_CATEGORY]
            match = _find_best_name_match(current, candidates)
        else:
            match = _find_category_match(current, prior_year_topics)

        if match is None:
            flagged.append(FlaggedTopic(
                topic_name=current.topic_name,
                category=current.category,
                status="NEW",
                current_mentions=current.mention_count,
                prior_mentions=0,
                source_quote=current.source_quote,
                quote_verified=False,  # set by verify step, not here
                prior_source_quote=None,  # no prior-year topic matched
                low_confidence=current.mention_count <= LOW_CONFIDENCE_MENTION_THRESHOLD,
            ))
        elif current.mention_count >= EXPANSION_MULTIPLIER * max(match.mention_count, 1):
            flagged.append(FlaggedTopic(
                topic_name=current.topic_name,
                category=current.category,
                status="EXPANDED",
                current_mentions=current.mention_count,
                prior_mentions=match.mention_count,
                source_quote=current.source_quote,
                quote_verified=False,
                prior_source_quote=match.source_quote,
                low_confidence=match.mention_count <= LOW_CONFIDENCE_MENTION_THRESHOLD,
            ))

    return flagged


def _find_category_match(topic: RiskTopic, candidates: list[RiskTopic]) -> RiskTopic | None:
    for candidate in candidates:
        if candidate.category == topic.category:
            return candidate
    return None


def _find_best_name_match(topic: RiskTopic, candidates: list[RiskTopic]) -> RiskTopic | None:
    best, best_score = None, 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, topic.topic_name.lower(), candidate.topic_name.lower()).ratio()
        if score > best_score:
            best, best_score = candidate, score
    return best if best_score >= SIMILARITY_THRESHOLD else None
