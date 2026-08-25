"""Tests for Track 2 Step 2: deterministic topic diffing."""
from edgar_risk_screener.schemas import RiskTopic, EMERGING_CATEGORY
from edgar_risk_screener.topic_diff import find_new_or_expanded_topics


def _topic(category, count, name=None, quote="sample quote text"):
    return RiskTopic(
        category=category,
        topic_name=name or category,
        mention_count=count,
        summary="summary",
        source_quote=quote,
    )


def test_flags_genuinely_new_fixed_category():
    prior = [_topic("Infrastructure and supply chain risk", 3)]
    current = [_topic("Infrastructure and supply chain risk", 3), _topic("AI-specific risk", 6)]

    flagged = find_new_or_expanded_topics(prior, current)

    assert len(flagged) == 1
    assert flagged[0].topic_name == "AI-specific risk"
    assert flagged[0].category == "AI-specific risk"
    assert flagged[0].status == "NEW"
    assert flagged[0].prior_mentions == 0
    assert flagged[0].low_confidence is False


def test_flags_expanded_fixed_category_at_2x_mentions():
    prior = [_topic("Cybersecurity risk", 4)]
    current = [_topic("Cybersecurity risk", 9)]

    flagged = find_new_or_expanded_topics(prior, current)

    assert len(flagged) == 1
    assert flagged[0].status == "EXPANDED"
    assert flagged[0].current_mentions == 9
    assert flagged[0].prior_mentions == 4
    assert flagged[0].low_confidence is False


def test_does_not_flag_stable_fixed_category():
    prior = [_topic("Competition and market risk", 5)]
    current = [_topic("Competition and market risk", 6)]  # small increase, well under 2x

    flagged = find_new_or_expanded_topics(prior, current)

    assert flagged == []


def test_fixed_category_matches_by_category_not_name():
    """Fixed-category topics are matched by category equality, not name
    similarity -- exact and deterministic, unlike the old fuzzy matching
    (see architecture.md limitation #2, now scoped to the emerging bucket)."""
    prior = [_topic("Infrastructure and supply chain risk", 5, name="Supply chain disruption")]
    current = [_topic("Infrastructure and supply chain risk", 6, name="Supply chain disruptions")]

    flagged = find_new_or_expanded_topics(prior, current)

    assert flagged == []  # matched by category, and 6 is not >= 2x 5


def test_emerging_topics_still_match_by_name_similarity():
    """The Emerging/unanticipated bucket keeps LLM-invented free-text names,
    so it still needs fuzzy matching -- this is the deliberate escape hatch
    that preserves Track 2B's "catch an unanticipated risk" purpose."""
    prior = [_topic(EMERGING_CATEGORY, 5, name="Quantum computing security risk")]
    current = [_topic(EMERGING_CATEGORY, 6, name="Quantum computing security risks")]

    flagged = find_new_or_expanded_topics(prior, current)

    assert flagged == []  # matched as the same topic, and 6 is not >= 2x 5


def test_emerging_topic_with_no_similar_prior_name_is_new():
    prior = [_topic(EMERGING_CATEGORY, 3, name="Space debris liability risk")]
    current = [_topic(EMERGING_CATEGORY, 4, name="Quantum computing security risk")]

    flagged = find_new_or_expanded_topics(prior, current)

    assert len(flagged) == 1
    assert flagged[0].status == "NEW"
    assert flagged[0].topic_name == "Quantum computing security risk"


def test_new_topic_backed_by_single_mention_is_low_confidence():
    """Empirically (3 runs of the same MSFT filing), every category that
    flickered in/out between runs had mention_count == 1 every time it
    appeared -- thin single-sentence mentions are the least stable case.
    Still flagged (not filtered), since a real new risk can start as one
    sentence, but marked low_confidence so it gets extra scrutiny."""
    prior = []
    current = [_topic("Tax risk", 1)]

    flagged = find_new_or_expanded_topics(prior, current)

    assert len(flagged) == 1
    assert flagged[0].status == "NEW"
    assert flagged[0].low_confidence is True


def test_expanded_topic_from_single_prior_mention_is_low_confidence():
    prior = [_topic("Litigation risk", 1)]
    current = [_topic("Litigation risk", 2)]  # hits the 2x bar, but off a thin base

    flagged = find_new_or_expanded_topics(prior, current)

    assert len(flagged) == 1
    assert flagged[0].status == "EXPANDED"
    assert flagged[0].low_confidence is True
