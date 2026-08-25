"""Fetch Risk Factors text from a company's 10-K filings.

New capability vs edgar_10k_research_agent: that project only ever needed
the LATEST 10-K. This screener needs the latest AND the prior year's, to
diff risk factor topics across periods.
"""
import os
from edgar import set_identity, Company

set_identity(os.environ.get("EDGAR_IDENTITY", "Your Name <you@example.com>"))


def get_risk_factors_two_periods(ticker: str) -> dict:
    """Return Risk Factors (Item 1A) text for the latest 10-K and the
    prior-year 10-K.

    Returns:
        {
            "current": {"text": str, "filing_date": str, "fiscal_year": int | None},
            "prior":   {"text": str, "filing_date": str, "fiscal_year": int | None},
        }

    Assumes annual 10-K filings, one per year -- the filing at index 1 in
    the company's 10-K filing history is treated as "prior year". This is
    a simplifying assumption: it does not verify the two filings are
    exactly one fiscal year apart (a company with an irregular filing
    history could break this). Worth hardening if used beyond well-behaved
    large-cap filers like MSFT.
    """
    company = Company(ticker)
    filings = company.get_filings(form="10-K")

    if len(filings) < 2:
        raise ValueError(
            f"{ticker}: need at least 2 historical 10-K filings to compare, found {len(filings)}"
        )

    current_filing = filings[0]
    prior_filing = filings[1]

    current_text = current_filing.obj()["1A"]
    prior_text = prior_filing.obj()["1A"]

    return {
        "current": {
            "text": current_text,
            "filing_date": str(current_filing.filing_date),
        },
        "prior": {
            "text": prior_text,
            "filing_date": str(prior_filing.filing_date),
        },
    }


if __name__ == "__main__":
    result = get_risk_factors_two_periods("MSFT")
    print(f"Current filing ({result['current']['filing_date']}): {len(result['current']['text'].split()):,} words")
    print(f"Prior filing ({result['prior']['filing_date']}): {len(result['prior']['text'].split()):,} words")
