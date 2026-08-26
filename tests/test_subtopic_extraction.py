"""Tests for deterministic native sub-topic extraction. is_heading_like()
was validated against four REAL uploaded 10-K filings (AMZN, MSFT, IBM,
ORCL) with zero false positives before this was written -- these tests
encode that validation as permanent regressions.
"""
from edgar_risk_screener.subtopic_extraction import is_heading_like, extract_subtopics


# --- is_heading_like: real headings from real filings, must be detected ---

def test_detects_real_amazon_style_headings():
    assert is_heading_like("We Face Intense Competition")
    assert is_heading_like("We Have Foreign Exchange Risk")
    assert is_heading_like("Operating Risks")
    assert is_heading_like("Legal and Regulatory Risks")


def test_detects_real_microsoft_style_headings():
    assert is_heading_like("STRATEGIC AND COMPETITIVE RISKS")
    assert is_heading_like("Competition in the technology sector")
    assert is_heading_like("GENERAL RISKS")


def test_detects_real_ibm_and_oracle_top_level_headings():
    assert is_heading_like("Risks Related to Our Business")
    assert is_heading_like("Business and Operational Risks")
    assert is_heading_like("Financial Risks")


# --- is_heading_like: real false positives found and fixed, must NOT be detected ---

def test_rejects_bare_page_numbers():
    """Real bug found in AMZN text: bare page numbers ('8', '9', '10')
    are short with no terminal punctuation, same shape as a real
    heading, and were being caught as false positives before the fix."""
    assert not is_heading_like("8")
    assert not is_heading_like("9")
    assert not is_heading_like("10")


def test_rejects_normal_body_sentences():
    assert not is_heading_like("Our businesses are rapidly evolving and intensely competitive.")


def test_rejects_bullets():
    assert not is_heading_like("•we do not continue to develop and release new products;")


def test_rejects_long_phrases_even_without_punctuation():
    long_phrase = " ".join(["word"] * 20)
    assert not is_heading_like(long_phrase)


def test_rejects_single_word():
    """A single word (even capitalized) isn't a real heading -- requires
    at least 2 words."""
    assert not is_heading_like("Overview")


# --- extract_subtopics: real structure from real AMZN text ---

AMAZON_REAL_EXCERPT = """Business and Industry Risks

We Face Intense Competition

Our businesses are rapidly evolving and intensely competitive, and we have many competitors across geographies.

Competition continues to intensify, including with the development of new business models.

We Have Foreign Exchange Risk

The results of operations of, and certain of our intercompany balances associated with, our international stores are exposed to foreign exchange rate fluctuations."""


def test_extract_subtopics_groups_body_under_correct_heading():
    subtopics = extract_subtopics(AMAZON_REAL_EXCERPT)

    assert "We Face Intense Competition" in subtopics
    assert "rapidly evolving and intensely competitive" in subtopics["We Face Intense Competition"]
    assert "Competition continues to intensify" in subtopics["We Face Intense Competition"]

    assert "We Have Foreign Exchange Risk" in subtopics
    assert "foreign exchange rate fluctuations" in subtopics["We Have Foreign Exchange Risk"]
    # body of one heading should NOT leak into another
    assert "foreign exchange" not in subtopics["We Face Intense Competition"].lower()


def test_extract_subtopics_preserves_order():
    subtopics = extract_subtopics(AMAZON_REAL_EXCERPT)
    headings = list(subtopics.keys())
    assert headings.index("Business and Industry Risks") < headings.index("We Face Intense Competition")
    assert headings.index("We Face Intense Competition") < headings.index("We Have Foreign Exchange Risk")


def test_content_before_first_heading_goes_to_intro():
    text = "Some boilerplate opening paragraph with no heading before it at all.\n\nA Real Heading\n\nBody text here."
    subtopics = extract_subtopics(text)
    assert "(intro)" in subtopics
    assert "boilerplate opening" in subtopics["(intro)"]


def test_repeated_heading_accumulates_body():
    text = "A Real Heading\n\nFirst body chunk.\n\nA Real Heading\n\nSecond body chunk, later in the document."
    subtopics = extract_subtopics(text)
    assert len(subtopics) == 1
    assert "First body chunk" in subtopics["A Real Heading"]
    assert "Second body chunk" in subtopics["A Real Heading"]
