# EDGAR Risk Screener

Screens a single company's latest 10-K against its own prior-year 10-K and
flags unusual changes -- in the numbers and in the risk factor language --
so an analyst knows where to look first.

Companion project to `edgar_10k_research_agent` (single-company deep
research). This project solves a different problem: prioritization across
what an analyst *doesn't* have time to read in full, not deep research on
one company.

## Problem

An analyst following a coverage list of many companies cannot read every
filing in full each quarter. Quiet but meaningful changes -- a margin
compression, a new risk topic -- can go unnoticed until they're large
enough to make headlines. This tool doesn't replace reading the filing, it
flags which parts of it deserve a closer look.

## What this does (Milestone 1: one ticker)

- **Track 1 (deterministic):** compares Revenue, GrossProfit-derived margin
  %, and NetIncome year-over-year using XBRL facts. No LLM. Flags any
  change beyond a fixed threshold.
- **Track 2 (LLM-assisted, grounded):** extracts risk topics from this
  year's and last year's Risk Factors text separately, then deterministically
  diffs the two topic lists to flag NEW or EXPANDED topics. Every flagged
  topic carries a verbatim source quote that is checked against the
  original text before being trusted.

Milestone 2 (a coverage list, run in a loop, ranked results) and Milestone
3 (a coverage-list UI) are scoped in `docs/architecture.md` but **not**
built here -- this repo is Milestone 1 only.

## What this explicitly does NOT do

- Does not predict returns or generate investment recommendations
- Does not replace reading the filing -- it prioritizes what to read
- A flag means "unusual change, worth a look", not "confirmed problem"

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in Azure OpenAI / Anthropic credentials
streamlit run app/streamlit_app.py
```

## Status

Milestone 1 prototype. Every flagged topic should be hand-verified against
the real filing before being trusted -- see `docs/architecture.md` for
known limitations (fixed KPI threshold, topic-name matching by string
similarity rather than meaning).

## License

MIT — see LICENSE.
