"""Diff between two years' native sub-topic headings (see
subtopic_extraction.py), with two layers:

1. TOPIC-LEVEL (deterministic, no LLM): fuzzy string matching
   (SequenceMatcher) to find genuinely NEW or REMOVED headings. Unlike
   Track 2's fixed-taxonomy diff (which abandoned fuzzy matching because
   LLM-invented category names drifted between RUNS of the same year's
   text), both years' headings here are extracted by the SAME
   deterministic function from two DIFFERENT real filings -- no
   run-to-run variance, only genuine year-to-year wording differences,
   which is exactly what fuzzy matching is for.

   Calibrated against two REAL reworded-heading pairs:
   - IBM: "...Data Protection" (current) vs "...Data Privacy" (prior) -- 0.887 similarity
   - Oracle: "...Common and Preferred Stock" (current) vs "...Common Stock" (prior) -- 0.825
     (reflects a real event -- Oracle issuing new preferred stock -- also independently
     confirmed by the fixed-taxonomy pipeline flagging "Financial and capital structure
     risk" as EXPANDED for the same filing)
   Both correctly match as continuing (reworded) topics, not NEW/REMOVED.

2. CONTENT-LEVEL, WITHIN a matched topic (LLM-assisted): for topics that
   match across years, diff_subtopic_content() asks an LLM to compare
   that ONE topic's two years of body text and identify content
   genuinely new this year. Deliberately scoped to a single topic per
   call, not the whole document -- the same principle that made Option
   A's paragraph-level classification far more stable than the original
   whole-document topic extraction: a bounded, single-topic comparison
   is a much narrower task than open-ended document synthesis.

   NOT yet tested for run-to-run stability (no majority voting here,
   unlike paragraph_classifier.py) -- flagged honestly, not assumed
   reliable until empirically checked the same way everything else in
   this project has been.
"""
import re
from difflib import SequenceMatcher
from typing import List
from pydantic import BaseModel, Field
from edgar_risk_screener.schemas import SubTopicChange

SIMILARITY_THRESHOLD = 0.6
BODY_PREVIEW_CHARS = 300

# Generic, non-substantive headings to exclude from diffing -- not real
# risk topics, just parsing/document artifacts.
BOILERPLATE_HEADINGS = {"(intro)"}

CONTENT_DIFF_PROMPT = """You are comparing two versions of the same risk
factor topic from a company's 10-K filing: one from last year's filing,
one from this year's.

Topic: {heading}

Last year's text:
{prior_text}

This year's text:
{current_text}

Identify content that appears in THIS YEAR's text but was NOT present in
LAST YEAR's text for this same topic -- genuinely new information, not
just rephrasing of the same point. List each new point as a short,
self-contained bullet (under 30 words). If nothing new was added this
year, return an empty list.
"""


class SubTopicContentDiffResult(BaseModel):
    new_points: List[str] = Field(
        default_factory=list,
        description="Short bullet points describing content newly mentioned this year "
                    "that was not in last year's text for this topic. Empty if nothing new.",
    )


def _is_boilerplate(heading: str) -> bool:
    if heading in BOILERPLATE_HEADINGS:
        return True
    normalized = heading.strip().lower()
    # catches "Item 1A. Risk Factors" / "ITEM 1A. RISK FACTORS" style
    # document title lines occasionally picked up as the first "heading"
    if normalized.startswith("item 1a") or normalized.startswith("item\xa01a"):
        return True
    return False


def diff_subtopic_content(heading: str, prior_text: str, current_text: str) -> SubTopicContentDiffResult:
    """Compare one matched topic's two years of body text via LLM. Import
    is local so this module stays importable without langchain installed.
    """
    from edgar_risk_screener.llm_provider import get_llm

    llm = get_llm()
    structured_llm = llm.with_structured_output(SubTopicContentDiffResult).with_retry(
        stop_after_attempt=5, wait_exponential_jitter=True,
    )
    prompt = CONTENT_DIFF_PROMPT.format(heading=heading, prior_text=prior_text, current_text=current_text)
    return structured_llm.invoke(prompt)


SKIPPED_SUMMARY_MESSAGE = "Summary skipped due to token usage management."


def compare_subtopics(
    prior_subtopics: "dict[str, str]",
    current_subtopics: "dict[str, str]",
    max_topics_to_process: int | None = None,
) -> list[SubTopicChange]:
    """Compare two years' {heading: body_text} mappings.

    Returns:
    - NEW headings (no good match in prior year) -- deterministic, no LLM,
      never limited by max_topics_to_process (there is no cost to ration)
    - REMOVED headings (no good match in current year) -- deterministic,
      same as above, never limited
    - UPDATED headings (matched a prior-year topic, and diff_subtopic_
      content() found genuinely new content) -- the ONLY step that costs
      an LLM call, and the only one max_topics_to_process governs
    - SKIPPED headings (matched a prior-year topic, but the LLM diff was
      not run because max_topics_to_process was reached) -- a placeholder
      message instead of real findings, with the real prior/current body
      text still attached so the analyst can read the original content
      themselves even without an LLM comparison of it

    max_topics_to_process counts MATCHED topics only, in current-year
    heading order (the order they're already iterated in below) -- the
    first N matched topics get a real diff_subtopic_content() call; any
    matched topics beyond that get SKIPPED instead. None (default) means
    no limit. 0 means process none (every matched topic is skipped). A
    large sentinel (e.g. 999, used by the UI) behaves as "no limit" without
    special-casing, since real filings have far fewer matched topics than
    that -- same convention as edgar_10k_research_agent's
    max_categories_to_summarize, after that project's initial version used
    a truthy check (`if max_topics_to_process:`) that silently treated 0
    as "no limit" instead of "process none", since 0 is falsy in Python.
    This uses `is not None` from the start to avoid repeating that bug.
    """
    prior_headings = [h for h in prior_subtopics if not _is_boilerplate(h)]
    current_headings = [h for h in current_subtopics if not _is_boilerplate(h)]

    matched_prior_headings: set[str] = set()
    changes: list[SubTopicChange] = []
    matched_topics_processed = 0

    for current_heading in current_headings:
        match = _find_best_match(current_heading, prior_headings)
        if match is None:
            changes.append(SubTopicChange(
                heading=current_heading,
                status="NEW",
                body_preview=current_subtopics[current_heading][:BODY_PREVIEW_CHARS],
            ))
        else:
            matched_prior_headings.add(match)

            if max_topics_to_process is not None and matched_topics_processed >= max_topics_to_process:
                changes.append(SubTopicChange(
                    heading=current_heading,
                    status="SKIPPED",
                    body_preview=current_subtopics[current_heading][:BODY_PREVIEW_CHARS],
                    new_points=[SKIPPED_SUMMARY_MESSAGE],
                    prior_full_text=prior_subtopics[match],
                    current_full_text=current_subtopics[current_heading],
                ))
                continue

            matched_topics_processed += 1
            content_diff = diff_subtopic_content(
                heading=current_heading,
                prior_text=prior_subtopics[match],
                current_text=current_subtopics[current_heading],
            )
            if content_diff.new_points:
                changes.append(SubTopicChange(
                    heading=current_heading,
                    status="UPDATED",
                    body_preview=current_subtopics[current_heading][:BODY_PREVIEW_CHARS],
                    new_points=content_diff.new_points,
                    prior_full_text=prior_subtopics[match],
                    current_full_text=current_subtopics[current_heading],
                ))

    for prior_heading in prior_headings:
        if prior_heading not in matched_prior_headings:
            changes.append(SubTopicChange(
                heading=prior_heading,
                status="REMOVED",
                body_preview=prior_subtopics[prior_heading][:BODY_PREVIEW_CHARS],
            ))

    return changes


def _find_best_match(heading: str, candidates: list[str]) -> str | None:
    best, best_score = None, 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, heading.lower(), candidate.lower()).ratio()
        if score > best_score:
            best, best_score = candidate, score
    return best if best_score >= SIMILARITY_THRESHOLD else None


# --- Sentence-level highlighting: deterministic, independent of the LLM ---
#
# This is NOT the same signal as diff_subtopic_content()'s new_points --
# it's a separate, purely mechanical check (SequenceMatcher on sentence
# pairs, no LLM at all) that flags which CURRENT-YEAR sentences have no
# close match anywhere in last year's text for the same topic. Useful as
# an independent cross-check: if the highlighted sentences roughly line
# up with what the LLM's new_points describe, that's corroborating
# evidence the content diff did a good job. If they diverge a lot (e.g.
# many highlighted sentences the LLM never mentioned, or vice versa),
# that's a real signal the LLM step needs scrutiny -- exactly the kind
# of independent verification this project has relied on throughout.

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
NEW_SENTENCE_SIMILARITY_THRESHOLD = 0.5  # below this, no good match in prior text


def split_into_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT_PATTERN.split(text) if s.strip()]


def find_new_sentences(prior_text: str, current_text: str) -> list[tuple[str, bool]]:
    """For every sentence in current_text, return (sentence, is_new),
    where is_new is True if no sufficiently similar sentence exists
    anywhere in prior_text. Purely mechanical -- SequenceMatcher pairwise
    comparison, no LLM involved.
    """
    prior_sentences = split_into_sentences(prior_text)
    current_sentences = split_into_sentences(current_text)

    results = []
    for sentence in current_sentences:
        best_score = 0.0
        for prior_sentence in prior_sentences:
            score = SequenceMatcher(None, sentence.lower(), prior_sentence.lower()).ratio()
            best_score = max(best_score, score)
        results.append((sentence, best_score < NEW_SENTENCE_SIMILARITY_THRESHOLD))

    return results
