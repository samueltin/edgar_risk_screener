"""Tests for the native sub-topic diff. The two fuzzy-match calibration
cases are REAL reworded headings found in real IBM and Oracle filings.

diff_subtopic_content() (the LLM-assisted within-topic content diff) is
monkeypatched to return no new points by default in tests that only care
about topic-level NEW/REMOVED behavior -- a real LLM call would otherwise
fire for every matched pair. Tests specifically for UPDATED status
monkeypatch it to return real points instead.
"""
from edgar_risk_screener.subtopic_diff import compare_subtopics, SubTopicContentDiffResult


def _no_new_content(heading, prior_text, current_text):
    """Stand-in for diff_subtopic_content: always reports nothing new."""
    return SubTopicContentDiffResult(new_points=[])


def test_real_ibm_reworded_heading_matches_not_flagged(monkeypatch):
    """Real IBM data: 'Data Protection' (current) vs 'Data Privacy'
    (prior) -- same topic, reworded, similarity 0.887. Must NOT be
    flagged as NEW or REMOVED at the topic level."""
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", _no_new_content)
    prior = {"Risks Related to Cybersecurity and Data Privacy": "prior body text"}
    current = {"Risks Related to Cybersecurity and Data Protection": "current body text"}

    changes = compare_subtopics(prior, current)

    assert changes == []


def test_real_oracle_reworded_heading_matches_not_flagged(monkeypatch):
    """Real Oracle data: 'Common and Preferred Stock' (current) vs
    'Common Stock' (prior) -- similarity 0.825, reflects a real event
    (new preferred stock issuance) but is still a CONTINUING topic at
    the heading level, not a new one."""
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", _no_new_content)
    prior = {"Risks Related to Our Common Stock": "prior body text"}
    current = {"Risks Related to Our Common and Preferred Stock": "current body text"}

    changes = compare_subtopics(prior, current)

    assert changes == []


def test_genuinely_new_heading_is_flagged(monkeypatch):
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", _no_new_content)
    prior = {"Risks Related to Our Business": "prior body"}
    current = {
        "Risks Related to Our Business": "prior body",
        "Risks Related to Artificial Intelligence Regulation": "a totally new topic",
    }

    changes = compare_subtopics(prior, current)

    assert len(changes) == 1
    assert changes[0].status == "NEW"
    assert changes[0].heading == "Risks Related to Artificial Intelligence Regulation"


def test_genuinely_removed_heading_is_flagged(monkeypatch):
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", _no_new_content)
    prior = {
        "Risks Related to Our Business": "body",
        "Risks Related to a Discontinued Product Line": "old topic, no longer discussed",
    }
    current = {"Risks Related to Our Business": "body"}

    changes = compare_subtopics(prior, current)

    assert len(changes) == 1
    assert changes[0].status == "REMOVED"
    assert changes[0].heading == "Risks Related to a Discontinued Product Line"


def test_identical_headings_produce_no_changes(monkeypatch):
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", _no_new_content)
    prior = {"Risks Related to Our Business": "a", "Financial Risks": "b"}
    current = {"Risks Related to Our Business": "a2", "Financial Risks": "b2"}

    changes = compare_subtopics(prior, current)

    assert changes == []


def test_intro_boilerplate_is_excluded_from_diffing():
    """No monkeypatch needed -- boilerplate is filtered before matching,
    so no LLM call happens at all for this case."""
    prior = {"(intro)": "boilerplate opening text"}
    current = {"(intro)": "different boilerplate opening text"}

    changes = compare_subtopics(prior, current)

    assert changes == []


def test_item_1a_title_line_is_excluded_from_diffing():
    prior = {"Item 1A. Risk Factors": "title artifact"}
    current = {"ITEM 1A. RISK FACTORS": "title artifact"}

    changes = compare_subtopics(prior, current)

    assert changes == []


def test_body_preview_is_included_for_new_heading():
    """No monkeypatch needed -- empty prior means no matches, no LLM call."""
    prior = {}
    current = {"A Brand New Topic": "This is the real body text an analyst would want to read."}

    changes = compare_subtopics(prior, current)

    assert len(changes) == 1
    assert "real body text" in changes[0].body_preview


# --- UPDATED status: LLM-assisted within-topic content diff ---

def test_matched_topic_with_new_content_is_flagged_as_updated(monkeypatch):
    def fake_content_diff(heading, prior_text, current_text):
        return SubTopicContentDiffResult(new_points=["A new fact only mentioned this year."])

    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", fake_content_diff)

    prior = {"Financial Risks": "last year's text about financial risk."}
    current = {"Financial Risks": "this year's text about financial risk, plus something new."}

    changes = compare_subtopics(prior, current)

    assert len(changes) == 1
    assert changes[0].status == "UPDATED"
    assert changes[0].heading == "Financial Risks"
    assert changes[0].new_points == ["A new fact only mentioned this year."]


def test_updated_change_includes_full_text_for_both_years(monkeypatch):
    """The full body text for both years must be attached to an UPDATED
    change, so the analyst can verify the LLM's claims against the real
    source text side by side, not just trust the bullet summary."""
    def fake_content_diff(heading, prior_text, current_text):
        return SubTopicContentDiffResult(new_points=["Something new."])

    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", fake_content_diff)

    prior = {"Financial Risks": "PRIOR YEAR FULL BODY TEXT"}
    current = {"Financial Risks": "CURRENT YEAR FULL BODY TEXT"}

    changes = compare_subtopics(prior, current)

    assert changes[0].prior_full_text == "PRIOR YEAR FULL BODY TEXT"
    assert changes[0].current_full_text == "CURRENT YEAR FULL BODY TEXT"


def test_new_and_removed_changes_do_not_populate_full_text_fields():
    """Full-text side-by-side comparison only makes sense for UPDATED
    (matched) topics -- NEW/REMOVED topics only exist in one year, so
    there's nothing to show side by side."""
    prior = {}
    current = {"A Brand New Topic": "some body text"}

    changes = compare_subtopics(prior, current)

    assert changes[0].status == "NEW"
    assert changes[0].prior_full_text == ""
    assert changes[0].current_full_text == ""


def test_matched_topic_with_nothing_new_is_not_reported(monkeypatch):
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", _no_new_content)

    prior = {"Financial Risks": "text"}
    current = {"Financial Risks": "text, lightly rephrased"}

    changes = compare_subtopics(prior, current)

    assert changes == []


def test_content_diff_called_with_correct_arguments(monkeypatch):
    captured = {}

    def capturing_content_diff(heading, prior_text, current_text):
        captured["heading"] = heading
        captured["prior_text"] = prior_text
        captured["current_text"] = current_text
        return SubTopicContentDiffResult(new_points=[])

    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.diff_subtopic_content", capturing_content_diff)

    prior = {"Tax Risks": "PRIOR YEAR TEXT"}
    current = {"Tax Risks": "CURRENT YEAR TEXT"}

    compare_subtopics(prior, current)

    assert captured["heading"] == "Tax Risks"
    assert captured["prior_text"] == "PRIOR YEAR TEXT"
    assert captured["current_text"] == "CURRENT YEAR TEXT"


# --- Sentence-level highlighting: deterministic, independent of the LLM ---

def test_split_into_sentences_basic():
    from edgar_risk_screener.subtopic_diff import split_into_sentences
    text = "First sentence here. Second sentence follows. Third one too!"
    sentences = split_into_sentences(text)
    assert sentences == [
        "First sentence here.",
        "Second sentence follows.",
        "Third one too!",
    ]


def test_find_new_sentences_flags_genuinely_new_sentence():
    from edgar_risk_screener.subtopic_diff import find_new_sentences

    prior_text = "We face competition in our core markets. Our margins may decline."
    current_text = "We face competition in our core markets. Our margins may decline. We are also investing heavily in a completely new AI compute strategy this year."

    results = find_new_sentences(prior_text, current_text)

    flagged_new = [s for s, is_new in results if is_new]
    assert len(flagged_new) == 1
    assert "AI compute strategy" in flagged_new[0]


def test_find_new_sentences_does_not_flag_reworded_but_similar_sentence():
    from edgar_risk_screener.subtopic_diff import find_new_sentences

    prior_text = "We face intense competition in our core markets."
    current_text = "We face significant competition in our core markets."

    results = find_new_sentences(prior_text, current_text)

    assert all(not is_new for _, is_new in results)


def test_find_new_sentences_flags_everything_when_prior_is_empty():
    from edgar_risk_screener.subtopic_diff import find_new_sentences

    results = find_new_sentences("", "This is a totally new topic with no prior text at all.")

    assert all(is_new for _, is_new in results)
