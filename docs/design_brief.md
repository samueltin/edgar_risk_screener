# EDGAR Risk Screener — Design Brief

**Purpose of this document:** a complete design spec for a second, separate
prototype, a companion project to `edgar_10k_research_agent` (Prototype 1),
reusing some of its components but solving a different business problem.

**Repo name:** `edgar_risk_screener`

## Status: Milestone 1 scaffolded, not yet run against live data

Milestone 1 (this document's full scope) has been scaffolded as a working
repo, including a Streamlit UI. This was confirmed explicitly: Milestone 1
was never backend-only, section 9's Streamlit layout **is** part of
Milestone 1, not a later addition.

**What exists in the repo already:**
- Full package structure under `src/edgar_risk_screener/` — `edgar_client/`
  (XBRL facts + the new two-period Risk Factors fetch), `schemas.py`,
  `llm_provider.py`, `kpi_change.py` (Track 1), `topic_extraction.py`
  (Track 2 Step 1, LLM), `topic_diff.py` (Track 2 Step 2, deterministic),
  `quote_verification.py`, `screener.py` (orchestration)
- `app/streamlit_app.py` — single-ticker UI matching section 9's layout
- `docs/architecture.md` — the four known limitations below, written up
  explicitly rather than left implicit
- `tests/` — 12 offline tests (no EDGAR or LLM calls) covering
  `kpi_change.py`, `topic_diff.py`, and `quote_verification.py`; all
  passing
- Lazy-import discipline confirmed: `topic_extraction.py` and
  `screener.py` import cleanly without `langchain`/`edgartools` installed,
  same pattern used (and needed) twice in Prototype 1

**What is explicitly NOT done yet, and is the reason for switching to
Claude Code Desktop:**
- Never run against a real ticker with live EDGAR/LLM calls — no API keys
  or local execution available in the environment that scaffolded this
- No hand-verification yet of any flagged topic against a real filing
  (the Milestone 1 verification step this whole design is built around)
- The two open thresholds (`UNUSUAL_CHANGE_THRESHOLD_PCT = 20.0` in
  `kpi_change.py`, `EXPANSION_MULTIPLIER = 2.0` and
  `SIMILARITY_THRESHOLD = 0.6` in `topic_diff.py`) are defaults from the
  design discussion, not calibrated against real data
- `filing_sections.py`'s "prior year = filings[1]" assumption (see section
  8 note) has not been tested against a real company's filing history

**Handoff instructions for Claude Code Desktop:**
1. Set up `.env` with real Azure OpenAI or Anthropic credentials and a
   real `EDGAR_IDENTITY`
2. Run `streamlit run app/streamlit_app.py` and screen MSFT first (same
   known-good test company used throughout Prototype 1)
3. Hand-verify every flagged topic against the actual MSFT 10-K Risk
   Factors text before trusting the output — same spot-check discipline
   used for Prototype 1's risk summary review, where a real units bug was
   caught this way
4. Treat section 10's open questions as things to surface back to the
   user, not silently pick reasonable-looking defaults for — that is
   exactly the kind of unstated assumption that caused the units mismatch
   bug in Prototype 1's segment extractor
5. Only after MSFT is verified, try a second company to sanity-check the
   `filing_sections.py` "prior year" assumption holds beyond one filer

---

## 1. Business problem

**Who has this problem:** a research analyst or portfolio manager following
a coverage list, a group of companies (typically 15–50) they track
regularly across one or more sectors.

**The problem today, without this tool:** an analyst cannot deeply read
every company's full filing every quarter. In practice:
- Companies with obvious news or headlines get read
- Quiet companies, no headline, no obvious trigger, often get skipped, even
  if something meaningful changed in their numbers or filing language
- Early warning signs can sit unnoticed in a filing for weeks or months,
  until the change is large enough to show up in the stock price or in the
  news, at which point it's too late to act early

**What this prototype does:** given a ticker (Milestone 1) or eventually a
coverage list (Milestone 2+), it compares the company's latest 10-K against
its own prior-year 10-K and flags what changed by an unusual amount, both
in the numbers (deterministic) and in the risk factor language
(LLM-assisted, with grounding).

**What this prototype explicitly does NOT do:**
- It does not predict stock returns or generate investment recommendations
- It does not replace reading the filing, it decides which filings (or
  which sections) are worth reading first
- It does not claim a flagged company has a real problem, only that
  something changed by an unusual amount and deserves a human look

**One-paragraph problem statement (for the README):**
> "An analyst following a coverage list of many companies cannot read every
> filing in full each quarter, so quiet but meaningful changes can go
> unnoticed until they become large enough to make headlines. This
> prototype screens a company's latest 10-K against its own prior filing
> and flags unusual changes in financial metrics and risk factor language,
> so the analyst knows where to look first. It does not replace analyst
> judgment, it directs a limited amount of analyst time toward the filings
> most likely to need it."

---

## 2. Relationship to Prototype 1 (`edgar_10k_research_agent`)

- **Reused as-is:** `edgar_client` fetch patterns (XBRL facts, filing
  sections), the lazy-import testing pattern (EDGAR/LLM-dependent imports
  kept local to functions so pure logic stays unit-testable offline), the
  LLM provider factory (Azure OpenAI / Anthropic swap), Streamlit UI
  conventions (status badges, expandable detail sections).
- **Genuinely new, not present in Prototype 1:** fetching **two filing
  periods** (latest + prior year) instead of one, topic-level extraction
  and diffing logic, deterministic YoY KPI threshold checks.
- **Deliberately a separate repo/project**, not a mode inside Prototype 1,
  because the business problem (coverage-list screening) and the trust
  model (deterministic-first, LLM as a secondary signal) are different
  enough to warrant their own C4 model and architecture notes.

---

## 3. Two-track signal design

Mirrors Prototype 1's XBRL-vs-LLM split, applied to change detection.

### Track 1: Deterministic numeric signals
Year-over-year (or quarter-over-quarter) change in XBRL figures (Revenue,
GrossProfit, NetIncome, gross margin %). Pure arithmetic, no LLM, fully
explainable. A change is "unusual" if it crosses a fixed threshold (e.g.
±20%) — simple and auditable, though a known simplification: it doesn't
account for a company's own historical volatility. Acceptable for the
MVP; worth stating explicitly as a limitation rather than hiding it.

### Track 2: Text-based signals — two sub-cases
- **2A. Known-term frequency (deterministic):** if you already know a term
  to track ("supply chain", "inflation"), counting its occurrences this
  year vs last year is plain text search — no LLM needed.
- **2B. Unknown/new topic detection (LLM-assisted):** catching a risk topic
  that's new this year, one the analyst didn't think to search for in
  advance, requires understanding meaning, not just matching a fixed word.
  This is the one genuinely new LLM component in this prototype.

**Design principle carried over from Prototype 1:** don't ask the LLM to
directly "compare two years of text" in one open-ended step (too much
surface area to get wrong, hard to audit). Instead:
- **Step 1 (LLM):** extract risk topics from ONE year's text at a time,
  each grounded with a short verbatim quote.
- **Step 2 (code):** compare the two topic lists deterministically.

---

## 4. Component design: topic extraction (LLM, Step 1)

### Schema
```python
class RiskTopic(BaseModel):
    topic_name: str = Field(description="A short, normalized name for this risk topic, e.g. 'Supply chain disruption'")
    mention_count: int = Field(description="Approximate number of distinct passages discussing this topic in the text")
    summary: str = Field(description="One sentence describing how the filing frames this risk")
    source_quote: str = Field(description="A short (under 20 words) verbatim quote from the text supporting this topic")

class RiskTopicExtraction(BaseModel):
    topics: List[RiskTopic]
```

### Prompt
```
You are analyzing the Risk Factors section of a 10-K filing. Identify the
distinct risk topics discussed in the text below.

For each topic:
- Give it a short, normalized name (so similar topics across different
  years can be compared later, e.g. always "Supply chain disruption", not
  sometimes "supply chain risk" and sometimes "vendor dependency").
- Count roughly how many separate passages discuss it.
- Summarize how the filing frames the risk, in one sentence.
- Include one short verbatim quote (under 20 words) as evidence.

Do not invent topics that are not actually discussed. Do not merge
unrelated risks into one topic just to shorten the list.

Text:
{risk_factors_text}
```

**Why the "normalized name" instruction matters:** it's what makes Step 2's
comparison possible at all — reduces (doesn't eliminate) the chance that
the same risk gets described with different wording across years.

Run this once per filing year (called twice: once for latest, once for
prior year).

---

## 5. Component design: topic diff (deterministic, Step 2)

```python
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.6  # topic names at least this similar count as "the same" topic

def find_new_or_expanded_topics(
    prior_year_topics: list[RiskTopic],
    current_year_topics: list[RiskTopic],
) -> list[dict]:
    flagged = []

    for current in current_year_topics:
        match = _find_best_match(current, prior_year_topics)

        if match is None:
            flagged.append({
                "topic_name": current.topic_name,
                "status": "NEW",
                "current_mentions": current.mention_count,
                "prior_mentions": 0,
                "source_quote": current.source_quote,
            })
        elif current.mention_count >= 2 * max(match.mention_count, 1):
            flagged.append({
                "topic_name": current.topic_name,
                "status": "EXPANDED",
                "current_mentions": current.mention_count,
                "prior_mentions": match.mention_count,
                "source_quote": current.source_quote,
            })

    return flagged


def _find_best_match(topic: RiskTopic, candidates: list[RiskTopic]) -> RiskTopic | None:
    best, best_score = None, 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, topic.topic_name.lower(), candidate.topic_name.lower()).ratio()
        if score > best_score:
            best, best_score = candidate, score
    return best if best_score >= SIMILARITY_THRESHOLD else None
```

**Known limitation, state explicitly in `architecture.md`:** string-based
topic-name matching (`SequenceMatcher`) will miss related topics phrased
very differently, and may falsely match unrelated ones with similar
wording. This is a concrete, well-motivated reason to consider embeddings
later (matching by meaning, not surface text) — unlike Prototype 1, where a
vector database was deliberately deferred as unnecessary, this prototype's
multi-period, multi-topic comparison is a genuine candidate for it down
the line. Not required for the MVP.

---

## 6. Grounding / quote verification (reused pattern from Prototype 1)

```python
def verify_quote(quote: str, source_text: str) -> bool:
    return quote.strip() in source_text
```

Any `source_quote` that fails this check should be flagged as unverified
(the topic might still be real, but the citation can't be trusted) — same
"don't silently trust unverified LLM output" principle as Prototype 1's
segment validator, applied to text instead of numbers.

---

## 7. Milestone plan

**Milestone 1 (build first): single ticker, two periods, Streamlit UI**
- Analyst enters one ticker
- System fetches latest 10-K + prior-year 10-K (both XBRL facts and Risk
  Factors text)
- Runs Track 1 (KPI YoY change) and Track 2B (topic extraction + diff) for
  that one company
- Displays results in Streamlit (see layout below)
- Hand-verify every flagged topic against the real filing text before
  trusting the logic — same spot-check discipline used for Prototype 1's
  risk summary review

**Milestone 2 (later): wrap in a loop over a coverage list**
- Same per-company logic, run for each ticker in a list
- Aggregate and rank results across companies (most topics flagged, or
  most severe KPI change, first)
- This is where a vector DB / batch infrastructure may start to earn its
  place — explicitly out of scope for Milestone 1

**Milestone 3 (later): coverage-list Streamlit view**
- Ranked table across companies, drill-down into each company's detail
  (reusing the Milestone 1 single-company view)

**This document specs Milestone 1 only.** Milestones 2–3 are noted for
context but not detailed further here.

---

## 8. Milestone 1 data flow

"Enter one ticker" triggers, in order:
1. Fetch latest 10-K's XBRL facts and Risk Factors text
2. Fetch prior-year 10-K's XBRL facts and Risk Factors text
3. Track 1: compute YoY change for Revenue, GrossProfit-derived margin %,
   NetIncome; flag any exceeding the fixed threshold (e.g. ±20%)
4. Track 2B: run topic extraction (LLM) on both years' Risk Factors text
5. Run the deterministic diff (`find_new_or_expanded_topics`)
6. Verify each flagged topic's quote against its source text
7. Display both tracks' results together in the UI

Note: this requires fetching **two** filings per ticker, unlike Prototype 1
which only ever looked at the latest filing — the "fetch prior year's
filing" logic is new and needs its own EDGAR client function.

---

## 9. Suggested Streamlit layout (Milestone 1)

```
┌───────────────────────────────────────────┐
│  Ticker input: [ MSFT ]  [Screen company]  │
├───────────────────────────────────────────┤
│  KPI Changes (deterministic)                │
│  Revenue:      +17.8% YoY   ✓ normal        │
│  Gross Margin: -0.9pp YoY   ✓ normal        │
│  Net Income:   +31.3% YoY   ⚠ unusual       │
├───────────────────────────────────────────┤
│  Risk Factor Changes (LLM-assisted)         │
│  🆕 NEW    AI regulatory uncertainty        │
│      6 mentions this year, 0 last year      │
│      "evolving legal and regulatory..."     │
│      ✓ quote verified                       │
│                                              │
│  📈 EXPANDED  Cybersecurity threats          │
│      9 mentions vs 4 last year               │
│      "increasingly sophisticated attacks..." │
│      ✓ quote verified                       │
└───────────────────────────────────────────┘
```

Two clearly separated sections matching the two tracks. The KPI panel
needs no disclaimer (deterministic, same trust level as Prototype 1's XBRL
data). The Risk Factor panel should carry a visible "LLM-assisted,
quote-verified" indicator per item — same transparency principle as
Prototype 1's validation badge.

---

## 10. Open design questions (not yet decided — flag to the user during build)

**Resolved:** whether Milestone 1 includes a Streamlit UI — yes, confirmed
explicitly, it is not a later addition. The UI is both the deliverable and
the tool used to hand-verify flagged output against real filings.

**Still open, listed below:**

- **KPI threshold rule:** fixed percentage (e.g. ±20%) vs relative to the
  company's own historical volatility. Fixed is simpler and more auditable
  (matches Prototype 1's validator style); relative is more accurate but
  adds real complexity. Default to fixed for the MVP, note the limitation.
- **Topic-name matching threshold:** is `SIMILARITY_THRESHOLD = 0.6` and
  the "2x mention count" EXPANDED rule the right calibration? Needs
  hand-testing against a real company's two consecutive filings (MSFT is
  the known-good test case from Prototype 1) before trusting it.
- **Quarter-over-quarter vs year-over-year:** this brief assumes annual
  (10-K vs prior 10-K). Quarterly (10-Q) screening was mentioned as a
  possible extension but not designed here.

---

## 11. Repo structure (as built)

```
edgar_risk_screener/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── docs/
│   ├── architecture.md      # known limitations, written up explicitly
│   └── design_brief.md      # this document
├── src/edgar_risk_screener/
│   ├── __init__.py
│   ├── schemas.py           # RiskTopic, RiskTopicExtraction, FlaggedTopic, KPIChange
│   ├── llm_provider.py      # Azure OpenAI / Anthropic factory
│   ├── kpi_change.py        # Track 1 — deterministic, no LLM
│   ├── topic_extraction.py  # Track 2 Step 1 — LLM, lazy-imported
│   ├── topic_diff.py        # Track 2 Step 2 — deterministic
│   ├── quote_verification.py
│   ├── screener.py          # orchestration, plain sequential calls
│   └── edgar_client/
│       ├── xbrl_facts.py         # reused pattern from Prototype 1
│       └── filing_sections.py    # NEW: fetches latest + prior-year filing
├── app/
│   └── streamlit_app.py     # Milestone 1 UI
├── tests/
│   ├── test_kpi_change.py
│   ├── test_topic_diff.py
│   └── test_quote_verification.py
└── notebooks/
```

**Follows the same discipline as `edgar_10k_research_agent`:** one
component per file, lazy imports for EDGAR/LLM dependencies so pure logic
stays unit-testable offline (confirmed working here, same as the fix
needed twice in Prototype 1), `docs/architecture.md` documenting design
decisions and known limitations rather than leaving them implicit.

**Still needed, per the handoff instructions above:**
- A `tests/golden_set/` (or similar) once Milestone 1 has been
  hand-verified against a real company's two filings, same pattern as
  Prototype 1's golden set
- Threshold calibration based on real MSFT output
- A second company tested, to sanity-check the "prior year = filings[1]"
  assumption in `filing_sections.py`
