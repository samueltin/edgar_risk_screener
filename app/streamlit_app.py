"""Streamlit UI: enter one ticker, see KPI changes and native sub-topic
changes compared against the company's prior-year 10-K.

Milestone 1 only -- one ticker at a time. See docs/architecture.md for
Milestone 2/3 (coverage list) scope, not built here.

Track 2 (fixed-taxonomy paragraph classification) has been fully
removed -- see docs/architecture.md for its history. Track 3 (native
sub-topic extraction) is the only risk-factor analysis track now.
"""
import sys
import html
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import streamlit as st
from edgar_risk_screener.screener import screen_company
from edgar_risk_screener.subtopic_diff import find_new_sentences


def _render_highlighted_text(prior_text: str, current_text: str) -> str:
    """Build an HTML string for the current-year text with sentences that
    have no good match anywhere in the prior-year text highlighted.

    This is a purely mechanical, deterministic signal (find_new_sentences,
    SequenceMatcher-based, no LLM) -- an independent cross-check against
    the LLM's own new_points bullets, not a restatement of them. If the
    highlighted sentences roughly line up with the bullets, that's
    corroborating evidence; if they diverge, that's worth investigating.
    """
    results = find_new_sentences(prior_text, current_text)
    parts = []
    for sentence, is_new in results:
        escaped = html.escape(sentence)
        if is_new:
            parts.append(f'<mark style="background-color:#fff3a3;">{escaped}</mark>')
        else:
            parts.append(escaped)
    return " ".join(parts)

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
                            "text for this topic, both years -- don't just trust the summary. "
                            "Highlighted sentences on the right have no close match anywhere in "
                            "last year's text -- a separate, mechanical check (no LLM), not a "
                            "restatement of the bullets above. If the highlights line up with "
                            "the bullets, that's reassuring; if they don't, look closer."
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Last year**")
                            st.write(change.prior_full_text)
                        with col2:
                            st.markdown("**This year**")
                            highlighted_html = _render_highlighted_text(
                                change.prior_full_text, change.current_full_text
                            )
                            st.markdown(highlighted_html, unsafe_allow_html=True)
            elif change.body_preview:
                st.caption(change.body_preview)

    st.info(
        "A flag means an unusual change worth a closer look, not a confirmed problem. "
        "Read the sub-topics and bullet points above in full, and verify them against "
        "the original text where shown, before drawing conclusions -- this tool "
        "prioritizes your attention, it doesn't replace reading the filing."
    )
