"""Deterministic access to SEC XBRL company facts.

Reused pattern from edgar_10k_research_agent: no LLM involved. Note that
edgartools' company facts already return several fiscal years in one call,
so unlike the Risk Factors text (below), we don't need a separate
"fetch prior period" step for KPI data -- one fetch gives us the history
needed for a year-over-year comparison.
"""
import os
from edgar import set_identity, Company

set_identity(os.environ.get("EDGAR_IDENTITY", "Your Name <you@example.com>"))


def get_income_statement(ticker: str):
    """Fetch normalized income statement facts for a ticker as a DataFrame,
    covering multiple fiscal years in one call.
    """
    company = Company(ticker)
    facts = company.get_facts()
    income_statement = facts.income_statement()
    return income_statement.to_dataframe(), company.name, company.cik


if __name__ == "__main__":
    df, name, cik = get_income_statement("MSFT")
    print(f"{name} ({cik})")
    print(df.head())
