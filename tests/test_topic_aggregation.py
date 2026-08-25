"""Tests for deterministic paragraph grouping and counting."""
from edgar_risk_screener.paragraph_classifier import ParagraphClassification
from edgar_risk_screener.topic_aggregation import group_paragraphs_by_category, mention_counts


def test_groups_paragraphs_by_category():
    paragraphs = ["para about competition", "para about cyber", "another competition para"]
    classifications = [
        ParagraphClassification(category="Competition and market risk"),
        ParagraphClassification(category="Cybersecurity risk"),
        ParagraphClassification(category="Competition and market risk"),
    ]

    grouped = group_paragraphs_by_category(paragraphs, classifications)

    assert len(grouped["Competition and market risk"]) == 2
    assert len(grouped["Cybersecurity risk"]) == 1


def test_mention_counts_matches_group_sizes():
    paragraphs = ["a", "b", "c"]
    classifications = [
        ParagraphClassification(category="Tax risk"),
        ParagraphClassification(category="Tax risk"),
        ParagraphClassification(category="Litigation risk"),
    ]

    grouped = group_paragraphs_by_category(paragraphs, classifications)
    counts = mention_counts(grouped)

    assert counts["Tax risk"] == 2
    assert counts["Litigation risk"] == 1


def test_raises_on_length_mismatch():
    try:
        group_paragraphs_by_category(["a", "b"], [ParagraphClassification(category="Tax risk")])
        assert False, "expected ValueError"
    except ValueError:
        pass
