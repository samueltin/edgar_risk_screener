"""Tests for screen_company's orchestration -- specifically that
max_topics_to_process actually reaches compare_subtopics(), not just that
screen_company() accepts the parameter.
"""


def test_max_topics_to_process_passed_through_to_compare_subtopics(monkeypatch):
    captured = {}

    def fake_get_income_statement(ticker):
        import pandas as pd
        return pd.DataFrame(), "Test Corp", "0000000000"

    def fake_compute_kpi_changes(df):
        return []

    def fake_get_risk_factors_two_periods(ticker):
        return {
            "current": {"text": "current text", "filing_date": "2026-01-01"},
            "prior": {"text": "prior text", "filing_date": "2025-01-01"},
        }

    def fake_extract_subtopics(text):
        return {"Some Topic": text}

    def fake_compare_subtopics(prior_subtopics, current_subtopics, max_topics_to_process=None):
        captured["max_topics_to_process"] = max_topics_to_process
        return []

    monkeypatch.setattr(
        "edgar_risk_screener.edgar_client.xbrl_facts.get_income_statement", fake_get_income_statement
    )
    monkeypatch.setattr("edgar_risk_screener.kpi_change.compute_kpi_changes", fake_compute_kpi_changes)
    monkeypatch.setattr(
        "edgar_risk_screener.edgar_client.filing_sections.get_risk_factors_two_periods",
        fake_get_risk_factors_two_periods,
    )
    monkeypatch.setattr("edgar_risk_screener.subtopic_extraction.extract_subtopics", fake_extract_subtopics)
    monkeypatch.setattr("edgar_risk_screener.subtopic_diff.compare_subtopics", fake_compare_subtopics)

    from edgar_risk_screener.screener import screen_company

    screen_company("TEST", max_topics_to_process=2)

    assert captured["max_topics_to_process"] == 2
