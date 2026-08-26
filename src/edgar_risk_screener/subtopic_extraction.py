"""Deterministic native sub-topic extraction from Risk Factors text.

No LLM at all -- unlike Track 2's paragraph classification into a fixed
external taxonomy, this reads the company's OWN heading structure
directly from the text. Real inspection of four companies' actual 10-K
Item 1A sections (AMZN, MSFT, IBM, ORCL, all user-uploaded) found each
uses a different convention:
- Amazon: standalone Title-Case heading lines, e.g. "We Face Intense
  Competition", own paragraph, no ending punctuation.
- Microsoft: ALL-CAPS top-level headers ("STRATEGIC AND COMPETITIVE
  RISKS") plus sentence-case short noun-phrase sub-headings
  ("Competition in the technology sector"), also standalone lines.
- IBM: "Title Case Heading: elaboration text" GLUED into one paragraph
  with a colon -- no separate line at all. NOT handled by this module;
  only IBM's 5 top-level category headers (which ARE standalone lines)
  get extracted here.
- Oracle: a dedicated "Risk Factor Summary" section with its own
  category headers, followed by a detailed section with no separate
  heading markers at all. NOT handled by this module; only Oracle's 6
  top-level category headers get extracted here.

is_heading_like() -- validated against all four real files with ZERO
false positives -- is the one signal common to Amazon's and Microsoft's
conventions: a heading is short and does NOT end in terminal sentence
punctuation, while every real body paragraph does. This single rule
gives FULL granularity for Amazon and Microsoft, and correctly (if only
coarsely) extracts IBM's and Oracle's top-level category names too.
Extracting IBM's colon-embedded headings and Oracle's Risk Factor
Summary content is a known, flagged follow-up -- not built here.

Because extraction is fully deterministic, there is NO run-to-run
instability in structure identification: the same real text always
produces the same headings, every time. This sidesteps entirely the
classification-flip instability that motivated the fixed-taxonomy
redesign's majority voting, minimum thresholds, etc.
"""
from collections import OrderedDict
from edgar_risk_screener.paragraph_splitter import _merge_bullet_lists, _merge_broken_sentences

BULLET_PREFIXES = ("•", "◦", "‣", "·")
TERMINAL_PUNCTUATION = ".!?:;\""
HEADING_MAX_WORDS = 15
MIN_CHUNK_CHARS = 3  # only drops truly empty/whitespace artifacts, NOT short real headings
                      # (e.g. "Operating Risks" is 15 chars -- far below the 40-char
                      # threshold paragraph_splitter.py uses for body-paragraph noise,
                      # which would incorrectly discard real short headings)


def is_heading_like(paragraph: str) -> bool:
    """A heading is short, doesn't end in terminal punctuation, isn't a
    bullet, and isn't a bare number (page-number artifact).
    """
    p = paragraph.strip()
    if not p or p.startswith(BULLET_PREFIXES):
        return False
    words = p.split()
    if len(words) < 2 or len(words) > HEADING_MAX_WORDS:
        return False
    if p[-1] in TERMINAL_PUNCTUATION:
        return False
    stripped = p.replace(",", "").replace(".", "").strip()
    if stripped.isdigit():
        return False
    return True


def extract_subtopics(text: str) -> "OrderedDict[str, str]":
    """Split text into chunks (reusing paragraph_splitter's bullet-merge
    and sentence-break-merge fixes so genuine structural artifacts don't
    corrupt heading detection), classify each chunk as heading or body,
    and group body text under the most recent heading.

    Returns an ordered mapping of heading -> concatenated body text (in
    first-seen order). Body chunks appearing before the first detected
    heading are collected under a "(intro)" key. If the same heading
    text appears more than once in the SAME text, its body accumulates
    rather than overwriting (relevant if a filing repeats a section
    title).
    """
    raw_chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) >= MIN_CHUNK_CHARS]
    chunks = _merge_bullet_lists(raw_chunks)
    chunks = _merge_broken_sentences(chunks)

    groups: "OrderedDict[str, list[str]]" = OrderedDict()
    current_heading = "(intro)"

    for chunk in chunks:
        if is_heading_like(chunk):
            current_heading = chunk
            groups.setdefault(current_heading, [])
        else:
            groups.setdefault(current_heading, []).append(chunk)

    return OrderedDict((heading, " ".join(body)) for heading, body in groups.items())
