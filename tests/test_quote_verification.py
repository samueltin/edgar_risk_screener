"""Tests for grounding: does a flagged topic's quote actually appear in
the source text."""
from edgar_risk_screener.schemas import FlaggedTopic
from edgar_risk_screener.quote_verification import verify_quote, verify_flagged_topics


def test_verify_quote_true_when_present():
    source = "We face intense competition across all markets for our products."
    assert verify_quote("intense competition across all markets", source) is True


def test_verify_quote_false_when_absent():
    source = "We face intense competition across all markets for our products."
    assert verify_quote("a completely fabricated quote", source) is False


def test_verify_flagged_topics_sets_flag_correctly():
    source = "Our AI models may be flawed, biased, or produce harmful outputs."
    topics = [
        FlaggedTopic(
            topic_name="AI-specific risk", category="AI-specific risk", status="NEW", current_mentions=3,
            prior_mentions=0, source_quote="AI models may be flawed, biased",
            quote_verified=False,
        ),
        FlaggedTopic(
            topic_name="Fabricated topic", category="Emerging or unanticipated risk", status="NEW", current_mentions=2,
            prior_mentions=0, source_quote="this text does not exist in source",
            quote_verified=False,
        ),
    ]

    result = verify_flagged_topics(topics, source)

    assert result[0].quote_verified is True
    assert result[1].quote_verified is False
