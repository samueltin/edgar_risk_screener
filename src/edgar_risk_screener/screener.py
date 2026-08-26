"""Orchestration: runs the full Milestone 1 pipeline for one ticker.

Track 2 (paragraph-level classification into a fixed 10-category
taxonomy) has been fully removed -- see docs/architecture.md for its
history (the Option A redesign, the coarse-taxonomy redesign, the
threshold recalibrations against real MSFT/AMZN/GOOG/IBM/ORCL data) and
why it was superseded by Track 3.

Track 3 (subtopic_extraction.py / subtopic_diff.py) is now the only risk-
factor analysis track: deterministic native sub-topic extraction (reads
the company's OWN heading structure, no LLM, no external taxonomy) plus
an LLM-assisted within-topic content diff for matched topics. Validated
against real MSFT, AMZN, IBM, and ORCL filings. GOOG's heading style
isn't handled by Track 3 -- screening GOOG's risk factors currently has
no working track; Track 2 would need to be restored from version control
history if GOOG support is needed again.

All EDGAR/LLM-dependent imports are local to this function, so the rest
of the package stays importable and unit-testable without
edgartools/langchain installed.
"""


def screen_company(ticker: str) -> dict:
    """Run the full screener for one ticker.

    Returns:
        {
            "ticker": str,
            "company_name": str,
            "kpi_changes": [KPIChange, ...],
            "subtopic_changes": [SubTopicChange, ...],
            "current_filing_date": str,
            "prior_filing_date": str,
        }
    """
    from edgar_risk_screener.edgar_client.xbrl_facts import get_income_statement
    from edgar_risk_screener.edgar_client.filing_sections import get_risk_factors_two_periods
    from edgar_risk_screener.kpi_change import compute_kpi_changes
    from edgar_risk_screener.subtopic_extraction import extract_subtopics
    from edgar_risk_screener.subtopic_diff import compare_subtopics

    # Track 1: deterministic KPI change
    df, company_name, _cik = get_income_statement(ticker)
    kpi_changes = compute_kpi_changes(df)

    periods = get_risk_factors_two_periods(ticker)

    # Track 3: deterministic native sub-topic extraction + LLM-assisted
    # within-topic content diff
    current_subtopics = extract_subtopics(periods["current"]["text"])
    prior_subtopics = extract_subtopics(periods["prior"]["text"])
    subtopic_changes = compare_subtopics(prior_subtopics, current_subtopics)

    return {
        "ticker": ticker,
        "company_name": company_name,
        "kpi_changes": kpi_changes,
        "subtopic_changes": subtopic_changes,
        "current_filing_date": periods["current"]["filing_date"],
        "prior_filing_date": periods["prior"]["filing_date"],
    }
