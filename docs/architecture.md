# Architecture

## Option A redesign (paragraph-level classification)

**This supersedes the original Track 2 design described below and in
`docs/design_brief.md`.** The original approach (whole-document topic
extraction: LLM reads the full Risk Factors text once per year and
invents topic names + estimates mention counts) was tested manually
against MSFT, run three times. Results were materially inconsistent
across runs: different topic sets flagged each time, and even a
"low_confidence" mitigation layered on top didn't fix it -- the
confidence badge itself flagged different topics as trustworthy each run,
which meant it was measuring within-run coherence, not actual
reproducibility.

**Root cause:** asking an LLM to both (a) decide topic boundaries/names
and (b) estimate mention counts, over a whole long document, in one
generation pass, is a synthesis task, not a classification task, even
when constrained to a fixed taxonomy of category names. Fixed labels
constrain vocabulary; they don't constrain how the model arrives at an
answer over the whole document.

**The fix -- change the shape of the task:**
1. `paragraph_splitter.py` (deterministic, no LLM) splits Risk Factors
   text into paragraphs.
2. `paragraph_classifier.py` (LLM, but narrow) classifies ONE paragraph
   into ONE category from `risk_taxonomy.py`'s fixed list. This is now a
   genuine classification task -- much more stable across repeated runs
   than whole-document synthesis.
3. `topic_aggregation.py` (deterministic) groups and counts classified
   paragraphs in code. Mention counts are no longer an LLM estimate --
   they're a tally, structurally incapable of the "roughly counting"
   instability from before.
4. `topic_diff.py` (deterministic, simplified) compares two years' count
   dictionaries directly -- no fuzzy string matching needed, since both
   years use the exact same fixed category vocabulary.

**A side benefit, not just a stability fix:** `FlaggedTopic` now carries
real `example_paragraphs` (actual classified text) instead of a
single LLM-picked quote that needed separate verification. Every count is
backed by the real paragraphs that produced it, by construction -- there
is nothing left to "verify" the way the old `quote_verification.py` had
to.

**Residual variance, honestly stated:** per-paragraph classification is
not perfectly reproducible either -- a paragraph near a category boundary
(e.g. "AI-specific risk" vs "Cloud and AI strategy risk") can still flip
between runs. The claim is not "zero variance," it's "small, bounded
variance" (a count moving by one or two) instead of "a topic's entire
existence flickering in and out." This has NOT yet been empirically
re-tested with three repeated runs the way the old design was -- that
re-test is the next concrete verification step, same discipline as every
other change in this project.

**Cost/latency trade-off, stated plainly:** this design makes many small
LLM calls (one per paragraph) instead of one large call per filing year.
Not yet measured against real filings; batching/concurrency is a
reasonable follow-up if latency becomes a problem in practice, not
addressed in this redesign to keep the change reviewable as one thing at
a time.

**Untested assumption carried into this redesign:**
`paragraph_splitter.py`'s blank-line splitting (with a single-newline
fallback) has not been confirmed against real `edgartools` HTML-to-text
output. If real MSFT Risk Factors text doesn't split cleanly into
sensible paragraphs, that's the first thing to check before trusting any
downstream classification.

---

## Scope: Milestone 1 only

This repo builds Milestone 1 from the design brief: a single ticker in, two
filing periods fetched (latest + prior year 10-K), results shown in
Streamlit. Milestone 2 (loop over a coverage list, ranked results) and
Milestone 3 (coverage-list UI) are intentionally not built here.

The rest of this document, below the Option A section above, describes
the ORIGINAL design (before the redesign). Kept for history/context —
the deterministic Track 1 (KPI change) content still applies unchanged.
filing periods fetched (latest + prior year 10-K), results shown in
Streamlit. Milestone 2 (loop over a coverage list, ranked results) and
Milestone 3 (coverage-list UI) are intentionally not built here.

## Why no LangGraph here (unlike edgar_10k_research_agent)

Prototype 1 uses LangGraph because it has a real branching pipeline
(validate -> pass/route to human review). This prototype's Milestone 1
flow is a straight sequence with no branching: fetch two periods -> compute
KPI changes -> extract topics twice -> diff -> verify quotes -> display.
Plain sequential function calls are easier to debug locally (per the
explicit reason for building this with Claude Code Desktop) and a graph
framework would add ceremony without solving a real branching problem
here. Worth revisiting if Milestone 2's loop-and-rank logic introduces
genuine branching (e.g. skip a ticker on fetch failure, continue the
batch).

## Two-track signal design

- **Track 1 (KPI change):** deterministic, reuses XBRL facts (already
  multi-year per ticker, no need to fetch "two periods" separately for
  this track -- edgartools' company facts already return several fiscal
  years in one call, same as edgar_10k_research_agent's xbrl_facts.py).
- **Track 2 (risk topic change):** LLM extracts topics per filing year
  (grounded with a verbatim quote), then a deterministic function diffs
  the two topic lists. The LLM is never asked to compare two years directly
  -- narrowing its job to single-document extraction keeps it auditable,
  same principle as why edgar_10k_research_agent's segment extractor
  doesn't self-reconcile against a total.

## Known limitations (state these plainly, don't hide them)

1. **Fixed KPI threshold (±20%), not relative to the company's own
   volatility.** Simple and auditable, but will under-flag volatile small
   companies and over-flag large stable ones less often than it should.
   Acceptable simplification for Milestone 1; a relative-volatility
   threshold is a reasonable Milestone 2+ improvement. Still applies —
   unaffected by the Option A redesign (Track 1 is unchanged).

2. **[SUPERSEDED by Option A, see top of this document]** Originally:
   topic matching used string similarity (`difflib.SequenceMatcher`) on
   LLM-invented topic names, which drifted between runs. Option A
   replaces this with paragraph-level classification against a fixed
   taxonomy, so category names never drift and the diff is now a plain
   dictionary comparison. Kept here as history — do not re-introduce
   fuzzy name matching without a real reason.

3. **[PARTIALLY ADDRESSED by Option A, see top of this document]**
   Originally: no ground truth for topic extraction, and single-quote
   verification only confirmed grounding, not correctness or
   completeness. Option A's `example_paragraphs` are the real classified
   text, not a separately-verified quote, which removes the grounding
   gap. What's still unresolved: no ground truth for whether a paragraph
   was classified into the *right* category, or whether the fixed
   taxonomy itself is complete for a given company's actual risks. Every
   flagged category should still be hand-checked against the real filing;
   see the golden-set pattern from edgar_10k_research_agent.

4. **Annual comparison only (10-K vs prior 10-K).** Quarter-over-quarter
   (10-Q) screening was discussed as a possible future direction but is
   not designed or built here.
