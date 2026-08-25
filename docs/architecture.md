# Architecture

## Scope: Milestone 1 only

This repo builds Milestone 1 from the design brief: a single ticker in, two
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
   threshold is a reasonable Milestone 2+ improvement.

2. **Topic matching uses string similarity (`difflib.SequenceMatcher`) on
   topic names, not semantic similarity.** This will miss genuinely related
   topics phrased very differently across years, and may occasionally
   false-match unrelated topics with similar wording. This is a concrete,
   well-motivated reason embeddings could be introduced later -- unlike
   edgar_10k_research_agent, where a vector database was deliberately
   judged unnecessary, this prototype's cross-period topic matching is a
   genuine future candidate. Not built in Milestone 1.

3. **No ground truth for topic extraction correctness.** Unlike Track 1
   (checkable against XBRL) or edgar_10k_research_agent's segment
   validator (checkable against a consolidated total), there is no
   deterministic way to confirm the LLM found every real topic, or that a
   topic's summary is accurate. Quote verification (does the cited text
   actually appear in the source) is a partial safeguard -- it confirms
   grounding, not correctness or completeness. Every flagged topic should
   be hand-checked against the real filing before being trusted; see the
   golden-set pattern from edgar_10k_research_agent.

4. **Annual comparison only (10-K vs prior 10-K).** Quarter-over-quarter
   (10-Q) screening was discussed as a possible future direction but is
   not designed or built here.
