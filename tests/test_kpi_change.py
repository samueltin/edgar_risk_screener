"""Tests for Track 1: deterministic KPI change detection."""
import pandas as pd
from edgar_risk_screener.kpi_change import compute_kpi_changes, UNUSUAL_CHANGE_THRESHOLD_PCT


def _sample_df():
    data = {
        "FY 2026": [331_839_000_000, 225_465_000_000, 133_749_000_000],
        "FY 2025": [281_724_000_000, 193_893_000_000, 101_832_000_000],
    }
    index = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "GrossProfit",
        "NetIncomeLoss",
    ]
    return pd.DataFrame(data, index=index)


def test_computes_revenue_change():
    changes = compute_kpi_changes(_sample_df())
    revenue = next(c for c in changes if c.metric_name == "Revenue")
    assert revenue.current_value == 331_839_000_000
    assert revenue.prior_value == 281_724_000_000
    assert revenue.pct_change > 0


def test_includes_derived_gross_margin_pct():
    changes = compute_kpi_changes(_sample_df())
    margin = next((c for c in changes if c.metric_name == "GrossMarginPct"), None)
    assert margin is not None
    assert 60 < margin.current_value < 80  # sanity range for MSFT-like margins


def test_flags_unusual_change_above_threshold():
    data = {"FY 2026": [1_500_000_000], "FY 2025": [1_000_000_000]}  # +50%
    df = pd.DataFrame(data, index=["NetIncomeLoss"])
    changes = compute_kpi_changes(df)
    net_income = changes[0]
    assert net_income.pct_change == 50.0
    assert net_income.unusual is True
    assert abs(net_income.pct_change) >= UNUSUAL_CHANGE_THRESHOLD_PCT


def test_does_not_flag_normal_change():
    data = {"FY 2026": [1_050_000_000], "FY 2025": [1_000_000_000]}  # +5%
    df = pd.DataFrame(data, index=["NetIncomeLoss"])
    changes = compute_kpi_changes(df)
    assert changes[0].unusual is False


def test_raises_with_fewer_than_two_fiscal_years():
    df = pd.DataFrame({"FY 2026": [1_000]}, index=["NetIncomeLoss"])
    try:
        compute_kpi_changes(df)
        assert False, "expected ValueError"
    except ValueError:
        pass
