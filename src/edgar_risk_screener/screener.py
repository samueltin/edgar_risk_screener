"""Orchestration: runs the full Milestone 1 pipeline for one ticker.

Plain sequential function calls, not LangGraph -- see docs/architecture.md
for why (no real branching logic exists yet at this milestone).

All EDGAR/LLM-dependent imports are local to this function, so the rest of
the package (schemas, kpi_change, topic_diff, quote_verification) stays
importable and unit-testable without edgartools/langchain installed.
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
    from edgar_risk_screener.topic_extraction import extract_risk_topics
    from edgar_risk_screener.topic_diff import find_new_or_expanded_topics
    from edgar_risk_screener.quote_verification import verify_flagged_topics

    # Track 1: deterministic KPI change
    df, company_name, _cik = get_income_statement(ticker)
    kpi_changes = compute_kpi_changes(df)

    # Track 2: LLM topic extraction (twice, one call per year) + deterministic diff
    periods = get_risk_factors_two_periods(ticker)
    current_extraction = extract_risk_topics(periods["current"]["text"])
    prior_extraction = extract_risk_topics(periods["prior"]["text"])

    flagged_topics = find_new_or_expanded_topics(
        prior_year_topics=prior_extraction.topics,
        current_year_topics=current_extraction.topics,
    )
    flagged_topics = verify_flagged_topics(flagged_topics, periods["current"]["text"], periods["prior"]["text"])

    return {
        "ticker": ticker,
        "company_name": company_name,
        "kpi_changes": kpi_changes,
        "flagged_topics": flagged_topics,
        "current_filing_date": periods["current"]["filing_date"],
        "prior_filing_date": periods["prior"]["filing_date"],
        "current_extraction": current_extraction,
        "prior_extraction": prior_extraction,
    }


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from dotenv import load_dotenv

    load_dotenv()

    ticker = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    result = screen_company(ticker)
    print("current_extraction:", result["current_extraction"])
    print("prior_extraction:", result["prior_extraction"])