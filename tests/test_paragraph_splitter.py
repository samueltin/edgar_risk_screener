"""Tests for deterministic paragraph splitting."""
from edgar_risk_screener.paragraph_splitter import split_into_paragraphs


def test_splits_on_blank_lines():
    text = "First paragraph, long enough to pass the minimum length filter.\n\nSecond paragraph, also long enough to pass the filter easily."
    paragraphs = split_into_paragraphs(text)
    assert len(paragraphs) == 2


def test_drops_short_fragments():
    text = "ITEM 1A.\n\nA real paragraph that is long enough to survive the minimum character filter easily."
    paragraphs = split_into_paragraphs(text)
    assert len(paragraphs) == 1
    assert "ITEM 1A." not in paragraphs


def test_falls_back_to_single_newline_for_long_text_with_no_blank_lines():
    # Simulates a long document with no double-newlines at all
    single_paragraph = "This is a long sentence that repeats. " * 20
    text = "\n".join([single_paragraph] * 10)
    paragraphs = split_into_paragraphs(text)
    assert len(paragraphs) > 1  # fallback should have kicked in
