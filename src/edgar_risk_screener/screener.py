"""Orchestration: runs the full Milestone 1 pipeline for one ticker.

Option A version: paragraph-level classification replaces whole-document
topic extraction (see docs/architecture.md for why). Plain sequential
function calls, not LangGraph -- no real branching exists at this
milestone.

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
            "flagged_topics": [FlaggedTopic, ...],
            "current_filing_date": str,
            "prior_filing_date": str,
        }
    """
    from edgar_risk_screener.edgar_client.xbrl_facts import get_income_statement
    from edgar_risk_screener.edgar_client.filing_sections import get_risk_factors_two_periods
    from edgar_risk_screener.kpi_change import compute_kpi_changes
    from edgar_risk_screener.paragraph_splitter import split_into_paragraphs
    from edgar_risk_screener.paragraph_classifier import classify_all_paragraphs
    from edgar_risk_screener.topic_aggregation import group_paragraphs_by_category, mention_counts
    from edgar_risk_screener.topic_diff import find_new_or_expanded_topics

    # Track 1: deterministic KPI change
    df, company_name, _cik = get_income_statement(ticker)
    kpi_changes = compute_kpi_changes(df)

    # Track 2 (Option A): paragraph-level classification, both years
    periods = get_risk_factors_two_periods(ticker)

    current_paragraphs = split_into_paragraphs(periods["current"]["text"])
    current_classifications = classify_all_paragraphs(current_paragraphs)
    current_grouped = group_paragraphs_by_category(current_paragraphs, current_classifications)

    prior_paragraphs = split_into_paragraphs(periods["prior"]["text"])
    prior_classifications = classify_all_paragraphs(prior_paragraphs)
    prior_counts = mention_counts(group_paragraphs_by_category(prior_paragraphs, prior_classifications))

    flagged_topics = find_new_or_expanded_topics(
        prior_year_counts=prior_counts,
        current_year_grouped=current_grouped,
    )

    return {
        "ticker": ticker,
        "company_name": company_name,
        "kpi_changes": kpi_changes,
        "flagged_topics": flagged_topics,
        "current_filing_date": periods["current"]["filing_date"],
        "prior_filing_date": periods["prior"]["filing_date"],
    }
