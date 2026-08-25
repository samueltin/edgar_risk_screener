"""Deterministic, structural splitting of Risk Factors text into
paragraphs. No LLM -- same output every time, by design.

This is Option A's foundation: since the LLM will classify one paragraph
at a time (not synthesize a topic list from the whole document), the
paragraph boundaries must be stable and reproducible, or the whole
redesign's stability guarantee falls apart at the first step.

KNOWN UNVERIFIED ASSUMPTION: this assumes edgartools' HTML-to-text
conversion produces blank-line-separated paragraphs. That has NOT been
confirmed against real filing output (the environment that built this
has no live EDGAR access). If splitting on "\n\n" yields too few
paragraphs from a real filing, the single-newline fallback below
activates -- but its output should be spot-checked against the actual
MSFT text before trusting it, same discipline as every other unverified
assumption in this project.
"""

MIN_PARAGRAPH_CHARS = 40   # filters out stray headers/whitespace fragments
FALLBACK_MIN_PARAGRAPHS = 5  # if double-newline split yields fewer than this, try single-newline


def split_into_paragraphs(text: str) -> list[str]:
    """Split on blank lines, dropping fragments too short to be a real
    risk-factor paragraph (e.g. bare sub-headings, page artifacts).

    Falls back to single-newline splitting if double-newline splitting
    produces suspiciously few paragraphs for a document this size --
    protects against silently treating a whole 10A section as "one
    paragraph" if the source text doesn't use blank-line breaks.
    """
    paragraphs = _split_on(text, "\n\n")

    if len(paragraphs) < FALLBACK_MIN_PARAGRAPHS and len(text) > 2000:
        paragraphs = _split_on(text, "\n")

    return paragraphs


def _split_on(text: str, separator: str) -> list[str]:
    raw_chunks = text.split(separator)
    return [p.strip() for p in raw_chunks if len(p.strip()) >= MIN_PARAGRAPH_CHARS]
