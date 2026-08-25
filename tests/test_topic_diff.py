"""Tests for Track 2 Step 2 (Option A): deterministic diff on category
mention counts. No SequenceMatcher needed -- both years share the exact
same fixed category vocabulary."""
from edgar_risk_screener.topic_diff import find_new_or_expanded_topics


def test_flags_genuinely_new_category():
    prior_counts = {"Supply chain risk": 3}
    current_grouped = {
        "Supply chain risk": ["p1", "p2", "p3"],
        "AI-specific risk": ["p4", "p5", "p6", "p7", "p8", "p9"],
    }

    flagged = find_new_or_expanded_topics(prior_counts, current_grouped)

    assert len(flagged) == 1
    assert flagged[0].topic_name == "AI-specific risk"
    assert flagged[0].status == "NEW"
    assert flagged[0].prior_mentions == 0
    assert flagged[0].current_mentions == 6


def test_flags_expanded_category_at_2x_mentions():
    prior_counts = {"Cybersecurity risk": 4}
    current_grouped = {"Cybersecurity risk": ["p"] * 9}

    flagged = find_new_or_expanded_topics(prior_counts, current_grouped)

    assert len(flagged) == 1
    assert flagged[0].status == "EXPANDED"
    assert flagged[0].current_mentions == 9
    assert flagged[0].prior_mentions == 4


def test_does_not_flag_stable_category():
    prior_counts = {"Competition and market risk": 5}
    current_grouped = {"Competition and market risk": ["p"] * 6}  # well under 2x

    flagged = find_new_or_expanded_topics(prior_counts, current_grouped)

    assert flagged == []


def test_example_paragraphs_are_capped():
    prior_counts = {}
    current_grouped = {"Tax risk": [f"paragraph {i}" for i in range(10)]}

    flagged = find_new_or_expanded_topics(prior_counts, current_grouped)

    assert flagged[0].current_mentions == 10          # real count, uncapped
    assert len(flagged[0].example_paragraphs) == 3     # display cap
