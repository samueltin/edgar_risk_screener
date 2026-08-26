"""Deterministic text-repair helpers, shared infrastructure used by
Track 3's native sub-topic extraction (subtopic_extraction.py).

Originally built for Track 2 (paragraph-level classification into a
fixed taxonomy, since removed) alongside a MIN_PARAGRAPH_CHARS-based
split_into_paragraphs() wrapper. That wrapper is gone -- its 40-char
minimum length filter was specifically wrong for Track 3's use case
(discards genuine short headings like "Operating Risks", 15 chars). The
two structural-repair functions below have no such conflict and remain
in active use.

BULLET-LIST FRAGMENTATION (real bug found in GOOG text): 10-K filings
often present a list of related risks as a bulleted list, where each
bullet is on its own blank-line-separated chunk following one intro
sentence. Naive splitting turns each bullet into its own isolated,
context-free fragment. _merge_bullet_lists() re-attaches each bullet to
its preceding paragraph.

MID-SENTENCE PAGE-BREAK SPLITS (real bug found in AMZN text): page
breaks in the source HTML sometimes fall mid-sentence, and the
conversion to plain text inserts a blank line at that exact point --
splitting a single sentence into two "paragraphs". Example from the
real AMZN filing: "...service disruptions, delays, setbacks, or
failures or" as one paragraph, "quality issues. In addition,
profitability..." as the next -- one sentence, artificially cut in
half. _merge_broken_sentences() detects and repairs this: if a
paragraph doesn't end in terminal punctuation AND the next paragraph
starts with a lowercase letter, they're almost certainly one sentence
that got split, and are merged back together.
"""

BULLET_PREFIXES = ("•", "◦", "‣", "·")
TERMINAL_PUNCTUATION = ".!?:;\""


def _merge_bullet_lists(paragraphs: list[str]) -> list[str]:
    """Re-attach any paragraph that starts with a bullet marker to the
    immediately preceding paragraph, so a bulleted list of related risks
    is read together with its introductory sentence, not as isolated,
    context-free fragments.

    A paragraph that IS the very first one and happens to start with a
    bullet (no preceding paragraph to attach to) is kept as-is -- rare
    edge case, not expected in practice since Risk Factors sections open
    with prose, not a bullet.
    """
    merged: list[str] = []
    for paragraph in paragraphs:
        if paragraph.startswith(BULLET_PREFIXES) and merged:
            merged[-1] = f"{merged[-1]} {paragraph}"
        else:
            merged.append(paragraph)
    return merged


def _merge_broken_sentences(paragraphs: list[str]) -> list[str]:
    """Re-attach a paragraph to the previous one if the previous one
    doesn't end in terminal punctuation and this one starts with a
    lowercase letter -- a strong signal they're one sentence that got
    split by a mid-sentence page break, not two genuinely separate
    paragraphs (a real new paragraph/topic starts with a capital letter).

    Run AFTER bullet merging: bullet items normally end in ";" or
    "; and" (terminal punctuation), so a correctly-merged bullet list
    won't be falsely caught here.
    """
    merged: list[str] = []
    for paragraph in paragraphs:
        if merged and _is_broken_sentence_continuation(merged[-1], paragraph):
            merged[-1] = f"{merged[-1]} {paragraph}"
        else:
            merged.append(paragraph)
    return merged


def _is_broken_sentence_continuation(prev: str, current: str) -> bool:
    prev, current = prev.rstrip(), current.lstrip()
    if not prev or not current or current.startswith(BULLET_PREFIXES):
        return False
    ends_mid_sentence = prev[-1] not in TERMINAL_PUNCTUATION
    starts_lowercase = current[0].islower()
    return ends_mid_sentence and starts_lowercase
