# Architecture

## Cost control: limit how many matched sub-topics get the LLM diff

**Why:** another cost lever, alongside Ollama -- a filing with many
matched sub-topics means one LLM call per matched topic
(diff_subtopic_content). `max_topics_to_process` caps how many of those
calls actually happen, in current-year heading order. NEW and REMOVED
topics are never limited -- they involve no LLM call at all, so there's
nothing to ration.

**Built the `is not None` check in from the start**, not a truthy check --
edgar_10k_research_agent's first version of the equivalent feature
(`max_categories_to_summarize`) used `if max_categories_to_summarize:`,
which silently treated `0` as falsy and therefore "no limit" instead of
the intended "process none" (found and fixed after the fact there). Same
`0` = process none / large sentinel (999, used by the UI) = process all
convention here, applied correctly the first time.

**A matched topic beyond the limit gets `status="SKIPPED"`**, with a
placeholder message (`new_points = ["Summary skipped due to token usage
management."]`) but its real `prior_full_text`/`current_full_text` still
populated -- the point is saving LLM cost, not hiding the analyst's
ability to read the original filing content. The Streamlit UI still
offers the side-by-side original-text view for a SKIPPED topic, since
that costs nothing extra (no LLM involved), including the deterministic
sentence-highlighting cross-check, which also runs for free.

---

## Ollama support added (cutting Azure OpenAI cost during development)

**Why:** same reason as edgar_10k_research_agent -- Azure OpenAI API cost
during active development. `llm_provider.get_llm()` gained an `"ollama"`
branch, identical pattern to the one already proven there: `langchain_
ollama.ChatOllama`, with `base_url`, `model`, and `num_ctx` confirmed as
real fields on that class (checked directly via `ChatOllama.model_fields`,
not assumed).

**`OLLAMA_NUM_CTX` defaults to 4096**, matching the one real, confirmed
data point from edgar_10k_research_agent's testing: an 8GB GPU running
`llama3.1:8b` reported exactly that context window, with 100% GPU
utilization and no demonstrated headroom to push it higher safely.

**What's different here, and genuinely lower-risk than edgar_10k_
research_agent's experience:** `diff_subtopic_content()` (subtopic_diff.py)
is the only caller of `get_llm()` in this project, and it's scoped to one
risk sub-topic's body text per call, not a whole MD&A document. edgar_10k_
research_agent's local-model problems (context truncation, fabricated
numbers) came specifically from sending large, whole-document text in one
call -- a fundamentally different, larger-scale problem than comparing
two years of one topic's text.

**Honest status: no context-overflow problem has been confirmed here.**
Some real sub-topics can still run long (e.g. Oracle's "Business and
Operational Risks" topic, which produced 30+ bullet points earlier in
this project's testing), so it's plausible a similar issue could surface
on a long enough topic -- but nothing has actually been built to guard
against it, since there's no real evidence yet that it's needed. If a real
Ollama run against a long topic shows truncated or degraded output, that
would be the point to add a provider-aware limit here too, not before.

---

## Sentence-level highlighting added to the side-by-side view

**What:** `subtopic_diff.py`'s `find_new_sentences()` splits both years'
body text into sentences and flags, for each CURRENT-year sentence,
whether any sufficiently similar sentence (SequenceMatcher ratio >= 0.5)
exists anywhere in the PRIOR year's text. The Streamlit side-by-side
view now highlights those sentences in the "This year" column.

**Why this is a separate, valuable signal, not just cosmetics:** this
check is entirely independent of `diff_subtopic_content()`'s LLM-
generated bullet points -- pure mechanical string comparison, no LLM
involved at all. That makes it a genuine cross-check: if the highlighted
sentences roughly correspond to what the bullets describe, that's
corroborating evidence the LLM did a reasonable job. If many highlighted
sentences aren't reflected in any bullet, or vice versa, that's a
concrete signal the content-diff step needs scrutiny -- exactly the kind
of independent verification this project has relied on throughout,
rather than trusting one LLM output to grade itself.

**Correctness note:** rendered via `unsafe_allow_html=True` in Streamlit
(needed for the `<mark>` highlight styling), so every sentence is passed
through `html.escape()` before being wrapped -- verified against a real
test case containing literal `<script>` and `&` characters (the kind of
stray formatting artifact that does occasionally appear in real filing
text) to confirm nothing except the app's own `<mark>` tags ever
renders as live HTML.

**Threshold note:** `NEW_SENTENCE_SIMILARITY_THRESHOLD = 0.5` is a
starting point, not empirically tuned against real filing text yet --
worth checking whether it over- or under-highlights once used on a real
UPDATED result.

---

## Track 2 fully removed (was: temporarily disabled)

**Decision:** after validating Track 3 (native sub-topic extraction)
strongly against real MSFT, AMZN, IBM, and ORCL data, Track 2
(paragraph-level classification into the fixed 10-category taxonomy)
was removed entirely, not just commented out.

**Files deleted:** `paragraph_classifier.py`, `topic_aggregation.py`,
`topic_diff.py`, `risk_taxonomy.py`, and their dedicated tests
(`test_paragraph_classifier_voting.py`, `test_paragraph_classifier_
concurrency.py`, `test_topic_aggregation.py`, `test_topic_diff.py`,
`test_classify_prompt.py`).

**Files trimmed, not deleted:**
- `paragraph_splitter.py` — the `split_into_paragraphs()` wrapper
  (Track-2-only; its 40-char minimum length filter was specifically
  wrong for Track 3's short-heading use case) is gone, but
  `_merge_bullet_lists()` and `_merge_broken_sentences()` remain — Track
  3's `subtopic_extraction.py` depends on them directly. Their real
  GOOG/AMZN regression tests were rewritten to call the helpers
  directly instead of through the now-removed wrapper (`test_
  paragraph_splitter.py`).
- `schemas.py` — `RiskTopic`, `RiskTopicExtraction`, and `FlaggedTopic`
  removed; `SubTopicChange` and `KPIChange` remain.
- `screener.py` — rewritten with only Track 1 (KPI) and Track 3
  (sub-topics) wired in. The `screen_company()` return dict no longer
  has `flagged_topics`, `current_mention_counts`, `prior_mention_
  counts`, or the paragraph-count diagnostic fields (all were Track-2
  or Track-2-diagnostic specific).
- `app/streamlit_app.py` — the commented Track 2 UI block and the
  now-orphaned "🔍 Debug: raw counts" panel (which referenced the
  now-removed dict keys) are both gone.

**GOOG support is now gone, not just deferred.** Track 2 was GOOG's only
working path (its heading style was explicitly out of scope for Track
3). Screening GOOG's risk factors currently produces no useful sub-topic
signal — Track 2 would need to be restored from version control history
(it was never in a public commit before this point in the project, so
practically this means rebuilding it, or waiting until Track 3 gains a
GOOG-compatible extraction strategy) if GOOG support is needed again.

**Everything else in this document below** is Track 2's history (the
Option A redesign, majority voting, the coarse-taxonomy redesign, real
IBM/Oracle threshold findings, etc.) — kept as a record of what was
tried and learned, not as documentation of code that still exists.

---

## Side-by-side verification added for UPDATED content diffs

**Why:** a real ORCL production run (not a test artifact) returned 30+
"newly mentioned" bullets for a single topic. Genuinely possible if
Oracle's AI-related disclosure expanded that much this year, but equally
possible the ungoverned content-diff LLM call (no majority voting, no
stability testing -- see below) is being too liberal, flagging
rephrasing as "new". No way to tell which without checking bullets
against the real source text.

**Fix:** `SubTopicChange` now carries `prior_full_text` and `current_
full_text` -- the REAL, complete body text for both years, populated
only for UPDATED (matched) topics, since that's the only status where
both years' text exists for the same topic. The Streamlit UI shows this
as a side-by-side two-column comparison in a collapsed expander below
each UPDATED topic's bullet list, so the analyst can verify each claim
against the actual filing text rather than trusting the LLM summary
alone.

**Copyright note:** this is genuine, freshly-fetched filing text
displayed by the RUNNING APP for the user's own analysis -- normal,
legitimate tool operation, distinct from the constraint on embedding
filing text verbatim in static code (which remains paraphrased
throughout this project, e.g. the few-shot examples).

**This is a verification tool, not a fix for the underlying question**
raised in the same real ORCL run: whether the content-diff LLM call is
actually accurate, or over-reporting. That still needs the real
spot-check (compare 2-3 surprising bullets against actual prior-year
text) and the repeated-run stability test flagged when this feature was
first built -- neither done yet.

---

## Track 2 temporarily disabled; Track 3 gets within-topic content diffing

**Decision:** with Track 3 (native sub-topic extraction) validated
strongly against real MSFT, AMZN, IBM, and ORCL data, Track 2 (paragraph
classification into the fixed 10-category taxonomy) is commented out --
not deleted -- in both `screener.py` and `streamlit_app.py`, while Track
3 is evaluated as the primary approach for these four companies. GOOG's
heading style isn't handled by Track 3 yet, so Track 2 must be
re-enabled before screening GOOG (both commented blocks are marked
clearly with re-enable instructions).

**What stayed on:** the deterministic paragraph split (`split_into_
paragraphs`) is still run, cheaply, purely for the diagnostic paragraph
counts in the debug panel -- the expensive part (LLM classification,
grouping, threshold diffing) is what's commented out. `flagged_topics`,
`current_mention_counts`, and `prior_mention_counts` are empty
placeholders while disabled, so nothing downstream breaks.

## New: LLM-assisted content diff WITHIN a matched sub-topic

**The gap this closes:** Track 3's topic-level NEW/REMOVED diff only
detects whether a whole topic appeared or disappeared. It was explicitly
flagged as NOT detecting content changes within a topic that continued
to exist -- e.g. Oracle's real preferred-stock news lived inside a topic
("Common Stock" -> "Common and Preferred Stock") that correctly matched
as continuing, so the topic-level diff alone never surfaced it.

**What's built (`subtopic_diff.py`):** for every matched topic pair
(same heading, or a close fuzzy match, across both years), `diff_
subtopic_content()` asks an LLM to compare that ONE topic's two years of
body text and identify content genuinely new this year. A new `SubTopic
Change` status, "UPDATED", is added when the LLM finds something; a
matched topic with nothing new stays silent, same "only report
actionable signals" principle used throughout this project.

**Why this is scoped narrowly, on purpose:** one call per MATCHED TOPIC,
not one call for the whole document. This follows the exact principle
that made Option A's paragraph-level classification far more stable than
the original whole-document topic extraction (see the Option A section
below) -- a bounded, single-topic comparison is a much narrower task
than open-ended document synthesis. For a filing with ~15-25 native
sub-topics, this means ~15-25 LLM calls total, far fewer than Track 2's
paragraph x votes x years call volume ever was.

**Explicitly NOT yet done, stated plainly:**
- No majority voting on this content diff (unlike `paragraph_
  classifier.py`'s per-paragraph classification) -- run-to-run stability
  of the LLM's "what's new" judgment has NOT been empirically tested.
  Given everything this project has learned about open-ended LLM
  judgments varying between runs, this should be assumed unstable until
  proven otherwise, not assumed reliable by default.
- Tests (`test_subtopic_diff.py`) monkeypatch `diff_subtopic_content`
  throughout -- they verify the WIRING (matched topics get diffed,
  unmatched ones don't, UPDATED only appears when there's something to
  report) but say nothing about real LLM output quality or stability.
  That requires the same real, repeated-run testing discipline used
  everywhere else in this project, not yet done for this feature.

---

## Track 3 added: deterministic native sub-topic extraction (no LLM)

**Origin:** direct observation, across four real uploaded filings
(AMZN, MSFT, IBM, ORCL), that each company organizes its Item 1A
section differently, but the SAME company uses the SAME structure
year over year. Instead of classifying paragraphs into an external
fixed taxonomy (Track 2, with all its threshold/boundary complexity),
Track 3 reads the company's OWN heading structure directly and compares
this year's list of native topics against last year's.

**Four real conventions found, from inspecting the actual files:**
- Amazon: standalone Title Case heading line, own paragraph, no ending
  punctuation (e.g. "We Face Intense Competition").
- Microsoft: ALL CAPS top-level headers + sentence-case short
  noun-phrase sub-headings, also standalone lines.
- IBM: "Title Case Heading: elaboration text" glued into ONE paragraph
  with a colon -- no line break at all.
- Oracle: a dedicated "Risk Factor Summary" section with Title Case
  category headers up top, then a detailed section with no separate
  heading markers (the same sentences reappear as plain paragraph-opening
  text).

**What's built (`subtopic_extraction.py`, `subtopic_diff.py`):**
`is_heading_like()` -- validated against all four real files with ZERO
false positives after fixing one real bug (bare page-number artifacts
like "8", "9", "10" were initially caught as false-positive headings,
same shape as a real heading; fixed by requiring at least 2 words and
rejecting pure numbers). This single rule gives FULL granularity for
Amazon and Microsoft, and correctly (if only coarsely -- their top-level
category names only) extracts IBM's and Oracle's structure too.

**Known gap, not yet built:** IBM's colon-embedded individual headings
and Oracle's Risk Factor Summary bullet-level content aren't extracted
-- only their 5-6 top-level categories are. A real, flagged follow-up,
not a blocker for shipping this now.

**Diffing (`compare_subtopics`):** fuzzy string matching (SequenceMatcher),
calibrated against two REAL reworded-heading pairs:
- IBM: "...Data Protection" (current) vs "...Data Privacy" (prior) --
  0.887 similarity, correctly matched as continuing, not flagged.
- Oracle: "...Common and Preferred Stock" (current) vs "...Common Stock"
  (prior) -- 0.825 similarity, correctly matched as continuing. This
  reflects a REAL event (Oracle's new Mandatory Convertible Preferred
  Stock) that the fixed-taxonomy Track 2 ALSO independently flagged
  ("Financial and capital structure risk" EXPANDED) -- two different
  methods converging on the same real signal.

**Why fuzzy matching is safe here, unlike Track 2's earlier abandoned
attempt at it:** Track 2's original fuzzy matching was removed because
LLM-INVENTED category names drifted between RUNS of the same year's
text -- pure noise. Here, both years' headings are extracted by the
SAME deterministic function from two DIFFERENT real filings. There is
NO run-to-run variance at all in this step -- the same real text always
produces the same headings, every time. Fuzzy matching here handles
genuine year-to-year wording differences, not run-to-run instability.

**Real end-to-end validation, all four real filings:** AMZN and MSFT
showed 23/24 and 15/16 EXACT heading matches across two real filing
years (the one difference in each being a trivial title-line parsing
artifact, not a real content difference). IBM showed 0 flagged changes
(its one real rewording correctly matched, not flagged). Oracle showed
1 flagged change ("Risk Factor Summary" as NEW), likely a test-harness
artifact from manually splitting a concatenated debug file rather than
using the real `edgar_client` fetch -- needs re-confirmation once
wired into a live run.

**Status: added as Track 3, running ALONGSIDE Track 2, not yet
replacing it.** No LLM calls at all, so negligible added cost/latency.
GOOG's heading style (short, normal sentence case, no distinguishing
signal beyond brevity) is NOT handled and was explicitly deferred by
the user -- Track 2 remains the only option there.

**What Track 3 does NOT do, stated plainly:** it only detects whether a
whole topic appeared or disappeared. It does not yet diff CONTENT within
a matched topic (e.g. Oracle's real preferred-stock news lives inside a
topic that correctly matched as "unchanged" at the heading level, since
the topic itself continued -- only its content changed). Within-topic
content diffing is a distinct, unbuilt next phase.

---

## Second Oracle run: real evidence of residual noise, and a transparency fix

**Real observation:** running Oracle a second time (same tool, no code
changes) produced a different flag set. "Financial and capital structure
risk" flagged in both runs (15/10, then 16/10). "Operational and supply
chain risk" flagged in run 1 (12/8) but NOT in run 2 (10/9). Total
paragraph counts were identical in both runs (89 current, 76 prior --
expected, since splitting is deterministic code with no LLM), so the
difference was entirely in a handful of paragraphs landing in a different
category between runs -- exactly the residual noise majority voting was
always expected to leave behind (see the Option A and voting sections
above), now seen concretely on a case that matters.

**Why one flag survived and the other didn't, precisely:** Financial's
run-1 numbers (15/10) cleared the relative threshold exactly (1.5x10=15)
but had real room on the absolute side (+5, well past the +3 floor) --
enough margin that small noise in run 2 (16 vs 15) didn't change the
outcome. Operational's run-1 numbers (12/8) landed EXACTLY on the
relative threshold (1.5x8=12) with no margin at all -- the thinnest
possible pass. Ordinary classification noise in run 2 (10/9, needing
13.5) was enough to erase it entirely. This wasn't a wrong flag in run 1,
it was a fragile one that never had room to survive a rerun.

**The real gap this exposed:** the UI displayed every flag with equal
weight, with no way to tell "this cleared by a landslide" from "this
barely cleared" without manually running the tool twice and comparing.

**Fix:** `topic_diff.describe_flag_margin()` -- a pure, deterministic
function (no LLM, no synthetic score) that shows the actual numbers
against the actual thresholds, e.g. "1.50x prior count (needed 1.5x) and
+5 paragraphs (needed +3)". Displayed under every flagged topic in
Streamlit as "Threshold check: ...". This is deliberately NOT a
confidence label -- the earlier `low_confidence` badge (see the
"Prompt fix" section above) was discredited specifically because it
measured within-run coherence, not cross-run reproducibility. Showing
the real numbers instead lets the analyst make that judgment themselves,
directly, the same transparency principle as the debug panel.

**What this does NOT fix:** Operational's flag is still gone from run 2
-- this feature makes marginal results visible, it doesn't make them more
stable. If margin turns out to correlate reliably with reproducibility
across more real runs, a reasonable future step would be requiring a
minimum margin (not just clearing the bar at all) before flagging --
untested, not implemented here.

---

## IBM/Oracle investigation resolved: two different findings, one real bug

**IBM: not a bug.** Real mention counts (via the new debug panel) showed
7 of 9 categories matching EXACTLY between current and prior year, and
the 8th differing by exactly 1 paragraph in the DECREASING direction.
Given the diff rules, zero flags is the mathematically correct output for
this data. This is a reassuring result, not a concerning one -- this
level of agreement suggests classification is behaving consistently, and
is also plausible on its own terms (IBM is a large, mature company likely
making only incremental year-to-year edits to its Risk Factors section,
unlike GOOG's fast-moving AI-driven risk narrative). One thing NOT ruled
out by this data alone: confirm `current_filing_date` and
`prior_filing_date` are genuinely ~1 year apart, to eliminate the
possibility of a fetch bug pulling the same filing twice (which would
also produce near-identical counts, for the wrong reason).

**Oracle: revealed a real, distinct threshold bug.** Two categories
showed genuine ~50% increases (Financial and capital structure risk:
10 -> 15; Operational and supply chain risk: 8 -> 12) that the
then-current `EXPANSION_MULTIPLIER = 2.0` completely missed, since
neither came close to literal doubling. This exposed something the
original threshold design didn't account for: **a flat 2x multiplier
behaves very differently depending on baseline size**. At a baseline of
2-3 (Tax, Human capital, Governance), doubling to 4-6 is trivial noise,
correctly filtered by `MIN_ABSOLUTE_INCREASE`. At a baseline of 10-20
(Oracle's larger categories), doubling is an unrealistically high bar --
real, material shifts happen well below 2x at that scale.

**Fix:** `EXPANSION_MULTIPLIER` lowered from 2.0 to 1.5, `MIN_ABSOLUTE_
INCREASE` (3) unchanged. Verified against the FULL real Oracle dataset
(not just the two categories in question): the two genuine increases are
now caught, while every other category in the same real dataset --
including several with real but smaller percentage changes (Macro +25%,
Legal +11%, Emerging and Governance small-baseline swings) -- correctly
stays filtered. See `test_real_ibm_near_identical_counts_correctly_flag_
nothing` and `test_real_oracle_data_now_catches_two_genuine_increases`
in `tests/test_topic_diff.py` for the exact real numbers used.

**Still a hypothesis, not a closed calibration.** 1.5x was chosen because
it's the minimum change that catches Oracle's two real signals without
catching its noise -- it has NOT been re-tested against MSFT, AMZN, or
GOOG to confirm it doesn't reintroduce flicker there (a lower multiplier
is, by construction, more sensitive, which is the direction that caused
problems before the thresholds existed at all). Re-test all five tickers
(MSFT, AMZN, GOOG, IBM, Oracle) before considering this settled.

---

## Diagnostic gap fixed: zero-flags results were previously unexplainable

**Real incident:** IBM and Oracle both returned zero flagged topics after
the 10-category redesign. No visibility existed into WHY -- the tool
could not distinguish "genuinely nothing changed" from "too little raw
paragraph volume to clear the new thresholds" from "something upstream
(fetch, splitting) silently returned little usable text". This is worth
taking seriously specifically because it happened on two different
companies at once, not written off as coincidence without evidence.

**Fix:** `screener.py` now returns `current_paragraph_count`,
`prior_paragraph_count`, `current_mention_counts`, and
`prior_mention_counts` alongside the existing results. The Streamlit app
shows these in a "🔍 Debug" expander. This doesn't fix the underlying
IBM/Oracle result -- it makes the result diagnosable, which is a
prerequisite to knowing whether there's actually a bug or not.

**Resolution: see the section above this one** -- the debug panel did
exactly its job, surfacing the real numbers that distinguished IBM's
genuine stability from Oracle's real threshold miss.

---

## Major redesign: 61 -> 10 categories, plus breadcrumbs (explicit request)

**Decision:** given everything real testing had found (all four flickering
categories sitting exactly on `MIN_MENTIONS_FOR_NEW`'s threshold),
prioritize stability over category specificity: collapse the 61-category
taxonomy down to 10 broad categories, and add "breadcrumbs" so a coarser,
less specific flag still points the analyst at exactly which real
paragraphs to go read -- the tool narrows down WHERE to look, the analyst
still reads and judges the content themselves.

### New taxonomy (10 categories)

`Strategic and competitive risk`, `Technology and AI risk`, `Operational
and supply chain risk`, `Legal, regulatory, and IP risk`, `Financial and
capital structure risk`, `Tax risk`, `Human capital risk`, `Governance and
ownership risk`, `Macro, geopolitical, and reputation risk`, `Emerging or
unanticipated risk`. See `risk_taxonomy.py`'s `CATEGORY_SCOPE_NOTES` for
exactly which of the old 61 categories folded into each broad one.

**Why this should help:** broad categories aggregate far more paragraphs
each, so individual paragraph misclassifications have much more room to
average out before flipping a category's NEW/EXPANDED status -- directly
targeting the "exactly 2 mentions, right on the threshold" mechanism
found in the manual-classification analysis above.

**Real trade-off, not fully solved by coarsening:** Tax risk and Human
capital risk were already close to standalone in the old 61-category
taxonomy (Tax was deliberately never merged, for signal reasons; Human
capital only absorbed a few small sub-categories). Both remain relatively
thin even under the new scheme and may still show some threshold
fragility. This is a known, accepted trade-off -- not silently ignored.

**Also fixed a real coverage gap:** the old 61-category taxonomy had
few-shot examples for only 6 categories; the other 55 had none at all.
With only 10 categories, every real category (all but the catch-all) now
has at least one anchoring example -- `test_every_real_category_has_at_
least_one_example` in `test_classify_prompt.py` is a direct regression
test for this.

### Threshold recalibration (`topic_diff.py`)

- `MIN_MENTIONS_FOR_NEW` raised 2 -> 3: a genuinely new BROAD risk should
  generate more than a couple of paragraphs if it's real and material
  across a category this wide.
- New `MIN_ABSOLUTE_INCREASE = 3` for EXPANDED: now requires BOTH the 2x
  relative jump AND a minimum absolute increase. Added specifically
  because Tax risk and Human capital risk (see trade-off above) stay thin
  even now -- without an absolute floor, a thin category going from 2 to
  4 mentions (technically 2x) would flag as "expanded" on what's likely
  just paragraph-splitting noise.

**Both numbers are a reasoned hypothesis, NOT yet empirically validated**
against real repeated-run testing on the new taxonomy. Re-test (3-4x per
ticker, same discipline as every prior threshold change) before trusting
these are well-tuned.

### Breadcrumbs (new capability)

`FlaggedTopic` now carries `example_paragraph_positions` (1-based index
of each example paragraph within the filing's full paragraph list) and
`total_paragraphs_in_filing`, populated by `topic_aggregation.py`
(tracks paragraph position, not just text) and `topic_diff.py`. The
Streamlit UI renders these as "📍 Paragraph 14 of 59" alongside the full
real paragraph text (not truncated), reframing the tool's role
explicitly: it points to where to look, the analyst reads the actual
content and forms their own judgment, rather than trusting a category
label or a summary.

**Note on copyright scope:** showing full real paragraph text in the
*deployed, running application* (fetched fresh from EDGAR at runtime for
the user's own analysis) is normal, legitimate tool operation -- distinct
from the constraint on embedding filing text verbatim in *static code*
(e.g. the few-shot examples), which remains paraphrased throughout this
project.

---

## Key finding: flickering categories confirmed structurally thin, not just ambiguous

**Method:** ran the real `split_into_paragraphs()` (with all current fixes:
bullet-merge, sentence-break-merge) against a full real GOOG 10-K Risk
Factors section (72 raw paragraphs → 59 after fragment repair), then
manually classified each of the 59 into the fixed taxonomy, applying the
same "single best-fitting category" rule given to the LLM.

**The finding:** all four categories that flickered across real 4-run
GOOG testing (Customer concentration risk, Access to capital markets and
financing risk, Ownership concentration and controlling shareholder risk,
Business continuity and disaster recovery risk) landed at **exactly 2
mentions each** — precisely on `MIN_MENTIONS_FOR_NEW`'s threshold, not
comfortably above it. This is a more precise diagnosis than the earlier
"these categories are semantically ambiguous" hypothesis: each rests on
exactly two real paragraphs in the entire ~13,000-word filing. If even
ONE of those two paragraphs is misclassified in a given run (plausible —
e.g. the data-center paragraph genuinely touches both "Business
continuity" and "Cybersecurity" themes), the count drops from 2 to 1,
falls below threshold, and the category vanishes from that run entirely.
This is a precise, evidence-based mechanism for the exact flicker pattern
observed, not a guess.

**Implication for future fixes:** lowering `MIN_MENTIONS_FOR_NEW` would
make this WORSE (more thin categories would qualify as NEW at all).
Raising it would filter out genuinely-real-but-thin signals like these
four entirely — a real trade-off, not a free fix. The few-shot examples
already added for these four categories are the right lever (reduce the
chance either of the two supporting paragraphs gets misclassified in the
first place), not a threshold change.

## Second finding: framing vs. sub-topic ambiguity (new failure mode)

**The finding:** a real paragraph, framed entirely as "risks from
acquisitions," lists sub-bullets that individually mention intellectual
property, data privacy, and tax liabilities as risks INHERITED from an
acquired company — not as independent topics. A model reading loosely
could misclassify this paragraph under "Intellectual property risk" or
"Tax risk" instead of "Acquisitions and integration risk," missing that
these are sub-risks within an acquisitions discussion. This is a
DIFFERENT failure mode from the count-threshold fragility above — it's
about classifying by a paragraph's overall framing, not by whichever
keyword happens to appear inside it.

**Fix:** added a 6th few-shot example to `FEW_SHOT_EXAMPLES`, paraphrased
from this real paragraph, teaching the framing-over-keyword distinction
directly.

## Minor artifact spotted (not yet fixed): section headings as paragraphs

During this same manual classification, one of the 59 "paragraphs" was
simply the section heading "Risks Related to Laws, Regulations, and
Policies" — a heading, not real content, but long enough (49 characters)
to pass `MIN_PARAGRAPH_CHARS = 40` and get sent to the classifier as if
it were a real risk statement. Minor (one heading in 59 real paragraphs)
but worth noting as a small, real gap: `paragraph_splitter.py` currently
has no way to distinguish a short heading from a short but genuine
sentence. Not fixed here — flagged for a future pass if heading
contamination turns out to matter in practice (e.g. if it noticeably skews
a category's count).

---

## Few-shot examples updated: grounded in real GOOG content, paraphrased not copied

**Request:** use the actual uploaded GOOG.txt / AMZN.txt filing text as
the source for the few-shot examples, instead of generic made-up
paragraphs, since examples grounded in the real ambiguous content should
anchor the model better than invented ones.

**What was actually done:** the five `FEW_SHOT_EXAMPLES` in
`paragraph_classifier.py` are now **paraphrases** of the real fact
patterns found in GOOG's actual 10-K (its real advertiser-revenue
concentration, its real dual/triple-class share structure and founder
voting control, its real debt/capital-markets language, its real
data-center/earthquake disaster-recovery disclosure, its real
cybersecurity/state-sponsored-attack language) — not the filing's actual
sentences copied verbatim. Verified: no example shares an unbroken
8-word run with the source text.

**Why paraphrase instead of verbatim copy:** reproducing a company's own
written filing text at length isn't something to embed in new code, even
though the filing is public and the user already has the file. This
isn't just a compliance point — it's arguably better engineering too:
few-shot examples work by teaching the model a *pattern*
(paragraph → category), not by matching exact phrasing. Anchoring
examples too tightly to one company's specific sentence structure risks
generalizing worse to other companies once Milestone 2's coverage list
is in scope; a paraphrase of the same fact pattern in different wording
is a more robust teaching example, not just a safer one.

**Known gap: no MSFT.txt was available.** Only `GOOG.txt` and `AMZN.txt`
were uploaded in the session that made this change — all five examples
are grounded in GOOG specifically (the ticker that actually showed the
flickering across 4 runs), not MSFT or AMZN. If MSFT's real content
would usefully diversify the examples, that's a reasonable follow-up once
that text is available.

---

## Rate limit hit + retry fix (real incident, same-day intensive testing)

**What happened:** during one day of intensive multi-run stability
testing (MSFT, AMZN, GOOG, several repeated runs each, at 3 votes per
paragraph and up to 10 concurrent calls), Azure OpenAI returned a 429
rate-limit error for the `gpt-4.1` deployment in `uksouth`. Expected
consequence of testing volume, not a code bug — a single Azure deployment
has a fixed per-minute request/token quota, and this project's design
(many small classification calls, multiplied by voting and concurrency)
generates real load fast during repeated testing.

**Real gap this exposed:** before this fix, a single rate-limit error on
ANY ONE of potentially hundreds of concurrent calls crashed the ENTIRE
screening run via an unhandled exception — discarding every paragraph
classification that had already succeeded. For a run that might make
600+ calls, failing completely because of one transient 429 partway
through is a real robustness problem, independent of the rate limit
itself.

**Fixes applied:**
1. `classify_paragraph()` now wraps the LLM call with LangChain's
   `.with_retry(stop_after_attempt=5, wait_exponential_jitter=True)` —
   a transient rate-limit error is now retried with exponential backoff
   instead of crashing the whole batch.
2. `MAX_CONCURRENT_CALLS` lowered from 10 to 5 — reduces how often the
   limit gets hit in the first place. Both values remain tunable; raise
   `MAX_CONCURRENT_CALLS` if your deployment's quota allows more
   throughput, lower it further if 429s persist even with retry.

**Not a complete fix for heavy usage.** Retry + lower concurrency reduces
the frequency and impact of rate limits but doesn't eliminate the
underlying constraint: a single Azure deployment has a fixed quota. If
this becomes a recurring problem during continued testing, the real fix
is requesting a quota increase for the deployment (Azure portal) or
reducing `VOTES_PER_PARAGRAPH` for less critical test runs — both outside
what this codebase alone can solve.

---

## Prompt fix: full taxonomy + few-shot examples (real 4-run GOOG data)

**Source:** real testing, 4 repeated runs on GOOG (after all prior fixes:
Option A, majority voting, MIN_MENTIONS_FOR_NEW, concurrency, bullet-merge,
sentence-break-merge). Results:
- Run 1: Customer concentration risk
- Run 2: Customer concentration risk, Access to capital markets and financing risk
- Run 3: Customer concentration risk, Ownership concentration and controlling shareholder risk
- Run 4: Business continuity and disaster recovery risk, Access to capital markets and financing risk

**What this ruled out:** a category appearing to be "stable" after only 3
runs (Customer concentration risk was in 3/3 early runs) was disproven by
run 4, where it vanished entirely and an unrelated category appeared
instead. Three runs was not enough to trust a signal as reproducible —
worth remembering for future stability claims on any ticker.

**Diagnosis:** the classification prompt never actually listed the
category names or showed any examples — it relied entirely on the
Pydantic `Literal[RiskCategory]` schema to constrain the OUTPUT FORMAT via
structured output / function-calling, which is not the same as helping
the model REASON about which category best fits an ambiguous paragraph.
Four categories that plausibly overlap in meaning for a company like
Alphabet (multi-class share structure touches both ownership concentration
and governance; capital access, business continuity, and customer
concentration all involve financial/operational resilience themes) had no
worked examples to anchor them, so classification for borderline
paragraphs touching these themes was left to the model's judgment alone.

**Fix:** `paragraph_classifier.py`'s `CLASSIFY_PROMPT` now explicitly
lists all 61 categories from `risk_taxonomy.py`, plus 5 few-shot examples
— one for each of the four categories that traded places across the real
runs above, plus one unrelated clear-cut example (Cybersecurity risk) to
establish the paragraph → category pattern. Examples are illustrative,
written for this prompt, not verbatim text from any real filing (avoids
reproducing filing content beyond what's needed, and keeps the examples
general enough to apply across companies, not just GOOG).

**Explicitly NOT claimed to be a complete fix.** This addresses one real
contributor (the model reasoning without seeing the full category list or
examples), but does not address the separate, structural fragility named
in `topic_diff.py`: a category resting on exactly `MIN_MENTIONS_FOR_NEW`
(2) mentions is fragile by construction, since one paragraph's
classification flipping is enough to cross that threshold, regardless of
how good the prompt is. This prompt fix may reduce how OFTEN a given
paragraph's classification flips, but a fragile threshold combined with
even a small remaining flip rate can still produce visible instability.

**Not yet re-tested.** The next concrete step is repeating the same
multi-run test on GOOG (4+ runs, same as the test that found this) to see
whether the four previously-flickering categories now land consistently.
If they don't, the next hypothesis to test is raising `MIN_MENTIONS_FOR_NEW`
from 2 to 3, or `VOTES_PER_PARAGRAPH` from 3 to 5 — both already flagged
as reasonable follow-ups if threshold fragility remains the dominant
cause.

---

## Second bug found and fixed: mid-sentence page-break splits (real AMZN text)

**Source:** the user uploaded real AMZN 10-K Risk Factors text for the
same kind of inspection that found the bullet-list bug. Found a second,
distinct structural artifact.

**The bug:** page breaks in the source HTML sometimes fall in the middle
of a sentence, and the conversion to plain text inserts a blank line at
that exact point — so a single sentence gets split into two
"paragraphs". Real example from the AMZN filing: "...service
disruptions, delays, setbacks, or failures or" as one paragraph,
"quality issues. In addition, profitability..." as the next. One
sentence, artificially cut in half, each piece incomplete on its own.

**Detection heuristic:** a paragraph that does NOT end in terminal
punctuation (`.!?:;"`) followed by a paragraph that starts with a
lowercase letter is almost certainly a broken sentence, not a genuine new
paragraph (a real new topic starts with a capital letter). This is
distinct from the bullet-list bug (detected by a bullet marker at the
start of a fragment) — `_merge_broken_sentences()` runs as a second pass,
after bullet merging, so correctly-merged bullet lists (which end in ";"
or "; and") aren't falsely caught by this heuristic.

**Measured impact, both real filings, combined with the bullet fix:**

| Ticker | Raw paragraphs | After bullet merge | After sentence-break merge | Total fragments fixed |
|---|---|---|---|---|
| AMZN | 277 | 153 (124 bullets) | 143 (10 broken sentences) | 134 (48%) |
| GOOG | 307 | 245 (62 bullets) | 229 (16 broken sentences) | 78 (25%) |

**Nearly half of AMZN's raw paragraphs (48%) were structural artifacts,
not real distinct risk-factor paragraphs** — either bullet fragments or
broken sentences. GOOG was 25%. Both are large enough that this is
plausibly a bigger source of the observed run-to-run instability than
anything addressed by the classification-level fixes (majority voting,
minimum mention threshold) — those fixes make classification more robust
to ambiguous input, but this fix reduces how much ambiguous input exists
in the first place.

**Not yet re-tested for actual stability impact**, same as the bullet
fix — the next concrete step is re-running the 3x-per-ticker test on
AMZN and GOOG with ALL fixes now in place (Option A, majority voting,
MIN_MENTIONS_FOR_NEW, concurrency, bullet-merge, sentence-break-merge) to
see how much the flip rate has actually dropped.

**What this does NOT claim to catch:** the detection heuristic is
deliberately simple (punctuation + capitalization), chosen because it's
transparent and auditable, not because it's guaranteed complete. A
sentence that happens to break at a point where the second half also
starts with a capitalized word (e.g. a proper noun) would not be
detected. This is a reasonable, evidence-based heuristic, not a
guarantee — if further real filings surface breaks this doesn't catch,
that's useful data for refining it further, not a sign the approach is
wrong.

---

## Bug found and fixed: bullet-list fragmentation (real GOOG text)

**Source:** the user uploaded real GOOG (Alphabet) 10-K Risk Factors text
after reporting instability specifically on this ticker. Direct
inspection of the real text found a concrete, measurable bug, separate
from (and likely larger than) the classification-flip issue the round-2
fixes targeted.

**The bug:** `paragraph_splitter.py` split on blank lines only. Real 10-K
filings often present a list of related risks as a bulleted list, each
bullet on its own blank-line-separated chunk, following one intro
sentence (e.g. GOOG's acquisitions section: "Some of the areas where we
face risks include:" followed by ~10 separate bulleted risk items). Naive
blank-line splitting turned each bullet into its own isolated paragraph,
stripped of the context that gives it meaning — e.g. "implementation of
controls ... at the acquired company" with no visible connection to
acquisitions at all.

**Measured impact, real GOOG filing:** before the fix, blank-line
splitting produced 307 paragraphs. 62 of them (20%) were bare bullet
fragments. After merging bullets into their preceding paragraph: 245
paragraphs. One in five paragraphs being sent to the classifier was a
context-free fragment.

**Why this plausibly explains much of the observed instability:** a
context-free fragment is inherently more ambiguous to classify than the
same content read with its intro sentence — exactly the kind of
borderline case that flips between runs under majority voting. Since 20%
of all paragraphs had this problem, this is likely a bigger contributor
to GOOG's instability than the classification-flip issue round 2's fixes
targeted, and may explain why GOOG was consistently less stable than
MSFT in testing (MSFT's filing style may use bulleted lists less).

**Fix:** `_merge_bullet_lists()` in `paragraph_splitter.py` re-attaches
any paragraph starting with a bullet marker (•, ◦, ‣, ·) to the
immediately preceding paragraph. Regression-tested directly against the
real GOOG bullet section (`tests/test_paragraph_splitter.py`), not a
synthetic approximation.

**A genuinely good side effect:** this also resolved the "unverified
assumption" flagged in earlier versions of this module — real GOOG text
confirms `edgartools`' HTML-to-text output DOES use blank-line paragraph
breaks, so the single-newline fallback path is confirmed unnecessary for
at least this real example.

**Not yet re-tested for actual stability impact.** This fix addresses a
real, measured input-quality problem, but has not yet been run through
the same 3x-per-ticker (MSFT/AMZN/GOOG) test that surfaced the original
instability. That re-test — now on top of ALL of: Option A, majority
voting, MIN_MENTIONS_FOR_NEW, concurrency, and this bullet-merge fix — is
the next concrete verification step.

---

## Performance fix: concurrent classification calls

**Real-world trigger:** majority voting (round 2 fix, above) made
screening impractically slow. A ~100-paragraph filing needs roughly
`paragraphs x votes x 2 years` LLM calls (~600), and running them
sequentially (waiting for each to finish before starting the next) meant
real wait times in the range of many minutes per screen.

**Fix:** `classify_all_paragraphs()` now runs every (paragraph, vote)
classification task CONCURRENTLY via `ThreadPoolExecutor`
(`MAX_CONCURRENT_CALLS = 10` by default), instead of one at a time. Same
total number of calls, same voting logic, same results -- this is purely
a latency fix, not an accuracy change. Verified with tests proving result
grouping stays correct by paragraph even when tasks complete out of
order (`tests/test_paragraph_classifier_concurrency.py`).

**Trade-off to watch:** running many calls at once can hit your LLM
provider's rate limits, which weren't a concern when everything ran
sequentially. If you see rate-limit errors, lower `max_workers` (passed
to `classify_all_paragraphs`); if your provider allows more concurrent
throughput, raising it will speed screening up further. Not yet tuned
against real Azure OpenAI / Anthropic rate limits — start conservative
and adjust based on what you actually see.

**Encouraging result from the same test round that surfaced the slowness:**
AMZN, run 3 times with majority voting + `MIN_MENTIONS_FOR_NEW` already
in place: 2 of 3 runs matched exactly (both empty), the third differed by
only one item. Compare to the pre-fix AMZN result (1, 2, 3 flagged items
across three runs — no two runs matched at all). The round-2 stability
fixes are working; the single remaining discrepancy is worth diagnosing
specifically (which category, NEW or EXPANDED) once re-testing resumes
at a usable speed.

---

## Stability fix round 2: majority voting + minimum mention threshold

**Real test data that motivated this** (3 repeated runs per ticker,
after Option A was already in place):
- MSFT: 2/3 runs matched exactly, 1 run differed by 1 item — much better
  than pre-Option-A, but not fully stable
- AMZN (first test): 1, 2, 3 flagged items across three runs — no two
  runs matched
- AMZN (second test, same ticker): 3/3 runs matched exactly
- GOOG (first test): 2/3 runs matched exactly, 1 run had 2 extra items
- GOOG (second test): 2 runs, one had 3 items, the other had those 3 plus
  3 more

**Diagnosis:** Option A made classification much more stable, but not
perfect — a small number of borderline paragraphs (plausibly fitting more
than one category) still flip classification between runs. Because
`topic_diff.py`'s NEW rule was a hard cutoff (prior count exactly 0), a
SINGLE paragraph flipping was sometimes enough to flip prior count between
0 and 1, which flips a category's NEW status entirely — a
disproportionate effect for such a small underlying change. Larger,
more established filers (MSFT) were less affected, since most of their
risk categories have counts well above any borderline; smaller/newer
filers had more categories sitting close to the cutoff points, where this
instability actually shows up.

**Two mitigations added, addressing the same root cause from two
directions:**

1. **Majority-vote classification** (`paragraph_classifier.py`,
   `classify_paragraph_with_voting`): each paragraph is now classified
   `VOTES_PER_PARAGRAPH` (default 3) times, and the majority answer wins.
   A paragraph must flip on a MAJORITY of votes to change the final
   label, not just one unlucky call. Trade-off: 3x more LLM calls for
   classification (on top of Option A's already-higher call count vs the
   original whole-document design) — a real latency/cost increase, not
   yet measured against live filings.

2. **Minimum mention threshold for NEW** (`topic_diff.py`,
   `MIN_MENTIONS_FOR_NEW = 2`): a category needs at least 2 current-year
   mentions before being flagged NEW, not just 1. This directly removes
   the single-paragraph fragility described above — a category resting
   on exactly one paragraph is inherently too thin a signal to trust,
   regardless of how it's classified.

**Not yet re-tested empirically.** These are targeted fixes based on a
clear diagnosis of the observed failure pattern, but have NOT yet been
re-run through the same 3x-per-ticker (MSFT/AMZN/GOOG) test that
surfaced the problem. That re-test is the next concrete verification
step — same discipline as every other change in this project: a fix is
not "done" until it's been tested the same way the bug was found.

**What this does NOT fix:** EXPANDED categories can still flip if a
paragraph moves prior count from, say, 3 to 4 near the 2x boundary for a
low-count category. `MIN_MENTIONS_FOR_NEW` only targets the NEW case
(prior=0), which was the specific pattern in the real test data above. If
re-testing shows EXPANDED flags are still unstable at low counts, a
similar minimum-count guard for EXPANDED is a reasonable next step.

---

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
