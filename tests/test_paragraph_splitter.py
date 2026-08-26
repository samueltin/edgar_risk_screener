"""Tests for the deterministic text-repair helpers (bullet-list merging,
mid-sentence break merging) shared by Track 3's native sub-topic
extraction. The Track-2-only split_into_paragraphs() wrapper has been
removed -- these tests call the merge helpers directly instead, using
raw \\n\\n splitting to build test fixtures the same way
subtopic_extraction.py does.

The bullet and broken-sentence tests use ACTUAL text from real GOOG and
AMZN 10-K filings (provided by the user) that surfaced these bugs -- not
synthetic approximations.
"""
from edgar_risk_screener.paragraph_splitter import _merge_bullet_lists, _merge_broken_sentences


# --- Bullet-list merging: regression test using real GOOG 10-K text ---
# (Acquisitions risk section, Feb 2026 filing, Item 1A -- see docs/architecture.md)

GOOG_ACQUISITIONS_SECTION = """Acquisitions, joint ventures, investments, and divestitures are important elements of our overall corporate strategy and use of capital, and these transactions could be material to our financial condition and operating results. We expect to continue to evaluate and enter into discussions regarding a wide array of such potential strategic arrangements, which could create unforeseen operating difficulties and expenditures. Some of the areas where we face risks include:

•diversion of management time and focus from operating our business to challenges related to acquisitions and other strategic arrangements;

•failure to obtain required approvals on a timely basis, if at all, from governmental authorities; conditions placed upon approval that could, among other things, delay or prevent us from completing a transaction, or otherwise restrict our ability to realize the expected financial or strategic goals of a transaction; or investigations or litigation by governmental authorities related to our acquisitions and other strategic arrangements;

•failure to successfully integrate the acquired operations, technologies, services, and personnel (including cultural integration and retention of employees) and further develop the acquired business or technology;

•implementation of controls (or remediation of control deficiencies), procedures, and policies at the acquired company;"""


def test_real_goog_bullet_list_merges_into_one_paragraph():
    """Before this fix: this text would split into 5 isolated paragraphs
    (1 intro + 4 context-free bullets). After: it should be 1 paragraph,
    so a reader sees the full context, not fragments."""
    raw_chunks = [c.strip() for c in GOOG_ACQUISITIONS_SECTION.split("\n\n") if c.strip()]
    merged = _merge_bullet_lists(raw_chunks)

    assert len(merged) == 1
    assert "Acquisitions, joint ventures" in merged[0]
    assert "diversion of management time" in merged[0]
    assert "implementation of controls" in merged[0]


def test_merge_bullet_lists_directly():
    fragments = [
        "Intro sentence introducing a list of risks, long enough to pass the filter.",
        "•first bullet point describing a specific risk in some detail here.",
        "•second bullet point describing another specific risk in detail.",
        "A completely unrelated new paragraph that starts fresh, not a bullet.",
    ]
    merged = _merge_bullet_lists(fragments)

    assert len(merged) == 2
    assert "first bullet" in merged[0]
    assert "second bullet" in merged[0]
    assert merged[1] == fragments[3]


def test_bullet_as_first_paragraph_is_kept_as_is():
    """Edge case: a bullet with nothing before it to merge into."""
    fragments = ["•a lone bullet with no preceding paragraph to attach to at all"]
    merged = _merge_bullet_lists(fragments)
    assert merged == fragments


# --- Broken-sentence merging: regression test using real AMZN 10-K text ---
# (Business and Industry Risks section, Feb 2026 filing -- see docs/architecture.md)

def test_real_amzn_mid_sentence_break_merges_correctly():
    """Before this fix: 'or' and 'quality issues...' would be two
    separate, incomplete paragraphs. After: one complete sentence."""
    fragments = [
        "We may have limited or no experience in our newer market segments, and our customers may not adopt our product or service offerings. These offerings, which can present new and difficult technology challenges, may subject us to claims if customers of these offerings experience, or are otherwise impacted by, service disruptions, delays, setbacks, or failures or",
        "quality issues. In addition, profitability or other intended benefits, if any, in our newer activities may not meet our expectations.",
    ]
    merged = _merge_broken_sentences(fragments)

    assert len(merged) == 1
    assert "failures or quality issues" in merged[0]


def test_does_not_merge_genuinely_separate_paragraphs():
    """A real paragraph boundary: prior ends with terminal punctuation,
    next starts with a capital letter -- must NOT be merged."""
    fragments = [
        "This is a complete sentence that ends properly with a period.",
        "This is a genuinely new paragraph starting with a capital letter.",
    ]
    merged = _merge_broken_sentences(fragments)
    assert merged == fragments


def test_does_not_merge_into_a_bullet():
    """A broken-looking paragraph followed by a bullet should NOT merge
    into the bullet -- bullet merging is handled separately, in the
    opposite direction (bullet attaches to what's BEFORE it)."""
    fragments = [
        "Some incomplete-looking paragraph ending without punctuation like this one",
        "•a bullet point that should not be merged here directly",
    ]
    merged = _merge_broken_sentences(fragments)
    assert len(merged) == 2  # unchanged -- bullet merging runs separately, before this
