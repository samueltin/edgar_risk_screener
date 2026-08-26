"""Streamlit UI: enter one ticker, see KPI changes and native sub-topic
changes compared against the company's prior-year 10-K.

Milestone 1 only -- one ticker at a time. See docs/architecture.md for
Milestone 2/3 (coverage list) scope, not built here.

Track 2 (fixed-taxonomy paragraph classification) has been fully
removed -- see docs/architecture.md for its history. Track 3 (native
sub-topic extraction) is the only risk-factor analysis track now.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st
from edgar_risk_screener.screener import screen_company

st.set_page_config(page_title="EDGAR Risk Screener", layout="wide")
st.title("EDGAR Risk Screener")
st.caption("Compares a company's latest 10-K against its prior-year 10-K and flags unusual changes.")

ticker = st.text_input("Ticker", value="MSFT").upper().strip()

if st.button("Screen company") and ticker:
    with st.spinner(f"Fetching two filing periods and analyzing {ticker}..."):
        st.session_state["result"] = screen_company(ticker)

result = st.session_state.get("result")

if result:
    st.header(result["company_name"])
    st.caption(
        f"Comparing filing dated {result['current_filing_date']} "
        f"against prior filing dated {result['prior_filing_date']}"
    )

    st.subheader("KPI changes (deterministic)")
    for change in result["kpi_changes"]:
        icon = "⚠️" if change.unusual else "✓"
        label = "unusual" if change.unusual else "normal"
        if change.metric_name == "GrossMarginPct":
            st.write(
                f"{icon} **{change.metric_name}**: {change.current_value:.1f}% "
                f"(prior {change.prior_value:.1f}%, moved {change.pct_change:+.1f} points) — {label}"
            )
        else:
            st.write(
                f"{icon} **{change.metric_name}**: {change.current_value:,.0f} "
                f"(prior {change.prior_value:,.0f}, {change.pct_change:+.1f}%) — {label}"
            )

    st.subheader("Sub-topic changes (native structure)")
    st.caption(
        "This reads the company's OWN risk-factor headings directly from the filing "
        "(no external categories) and compares this year's topics against last year's. "
        "NEW/REMOVED topic detection is fully deterministic (no LLM, fully reproducible "
        "run to run). UPDATED entries use an LLM to compare a matched topic's two years "
        "of text and are not yet verified for run-to-run stability."
    )
    if not result["subtopic_changes"]:
        st.write("No sub-topic changes detected compared to the prior filing.")
    for change in result["subtopic_changes"]:
        icon = {"NEW": "🆕", "REMOVED": "🗑️", "UPDATED": "🔄"}.get(change.status, "•")
        with st.container(border=True):
            st.write(f"{icon} **{change.status}** — {change.heading}")
            if change.status == "UPDATED" and change.new_points:
                st.caption("Newly mentioned this year (not present last year):")
                for point in change.new_points:
                    st.write(f"- {point}")

                if change.prior_full_text and change.current_full_text:
                    with st.expander("🔍 Verify against original text (side by side)"):
                        st.caption(
                            "Check the bullet points above directly against the real filing "
                            "text for this topic, both years -- don't just trust the summary."
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Last year**")
                            st.write(change.prior_full_text)
                        with col2:
                            st.markdown("**This year**")
                            st.write(change.current_full_text)
            elif change.body_preview:
                st.caption(change.body_preview)

    st.info(
        "A flag means an unusual change worth a closer look, not a confirmed problem. "
        "Read the sub-topics and bullet points above in full, and verify them against "
        "the original text where shown, before drawing conclusions -- this tool "
        "prioritizes your attention, it doesn't replace reading the filing."
    )
