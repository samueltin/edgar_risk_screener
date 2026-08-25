"""Streamlit UI: enter one ticker, see KPI changes and flagged risk topics
compared against the company's prior-year 10-K.

Milestone 1 only -- one ticker at a time. See docs/architecture.md for
Milestone 2/3 (coverage list) scope, not built here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from edgar_risk_screener.schemas import EMERGING_CATEGORY
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

    st.subheader("Risk factor changes (LLM-assisted, quote-verified)")
    if not result["flagged_topics"]:
        st.write("No new or significantly expanded risk topics detected.")
    for topic in sorted(result["flagged_topics"], key=lambda t: t.topic_name.lower()):
        icon = "🆕" if topic.status == "NEW" else "📈"
        verified_badge = "✓ quote verified" if topic.quote_verified else "⚠ quote NOT verified in source text"

        with st.container(border=True):
            st.write(f"{icon} **{topic.status}** — {topic.topic_name}")
            if topic.category == EMERGING_CATEGORY:
                st.caption("🧭 Emerging category — not part of the fixed taxonomy, extra scrutiny recommended")
            else:
                st.caption(topic.category)
            st.write(f"{topic.current_mentions} mentions this year, {topic.prior_mentions} last year")
            if topic.low_confidence:
                st.caption("🔍 Low confidence — based on a single mention, verify carefully before trusting")

            with st.expander("Show source text (for hand verification)"):
                st.markdown("**This year:**")
                st.caption(f"\"{topic.source_quote}\"")
                if topic.quote_verified:
                    st.success(verified_badge)
                else:
                    st.warning(verified_badge)

                st.markdown("**Last year:**")
                if topic.prior_source_quote:
                    prior_verified_badge = (
                        "✓ quote verified" if topic.prior_quote_verified
                        else "⚠ quote NOT verified in source text"
                    )
                    st.caption(f"\"{topic.prior_source_quote}\"")
                    if topic.prior_quote_verified:
                        st.success(prior_verified_badge)
                    else:
                        st.warning(prior_verified_badge)
                else:
                    st.caption("No matching topic found in the prior-year filing.")

    st.info(
        "A flag means an unusual change worth a closer look, not a confirmed problem. "
        "Hand-verify flagged topics against the original filing before acting on them."
    )
