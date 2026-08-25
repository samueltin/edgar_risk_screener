"""Track 1: deterministic year-over-year KPI change detection.

No LLM. Pure arithmetic on XBRL-derived figures. Uses a fixed percentage
threshold -- see docs/architecture.md's "Known limitations" section for
why this is a simplification, not the final word on what counts as
"unusual".
"""
import pandas as pd
from edgar_risk_screener.schemas import KPIChange

UNUSUAL_CHANGE_THRESHOLD_PCT = 20.0  # fixed threshold, see architecture.md limitation #1

TARGET_CONCEPTS = {
    "RevenueFromContractWithCustomerExcludingAssessedTax": "Revenue",
    "GrossProfit": "GrossProfit",
    "NetIncomeLoss": "NetIncome",
}


def compute_kpi_changes(df: pd.DataFrame) -> list[KPIChange]:
    """Compute YoY % change for each target concept between the two most
    recent fiscal years present in the DataFrame. Also derives a
    GrossMarginPct change from Revenue and GrossProfit.
    """
    fy_columns = sorted(
        (col for col in df.columns if str(col).startswith("FY ")),
        key=lambda c: int(str(c).replace("FY ", "")),
        reverse=True,
    )
    if len(fy_columns) < 2:
        raise ValueError(f"Need at least 2 fiscal years to compute change, found {len(fy_columns)}")

    current_col, prior_col = fy_columns[0], fy_columns[1]

    values: dict[str, dict[str, float]] = {}
    for concept, metric_name in TARGET_CONCEPTS.items():
        if concept not in df.index:
            continue
        row = df.loc[concept]
        current_val, prior_val = row.get(current_col), row.get(prior_col)
        if pd.isna(current_val) or pd.isna(prior_val):
            continue
        values[metric_name] = {"current": float(current_val), "prior": float(prior_val)}

    changes = [_build_change(name, v["current"], v["prior"]) for name, v in values.items()]

    if "Revenue" in values and "GrossProfit" in values:
        current_margin = values["GrossProfit"]["current"] / values["Revenue"]["current"] * 100
        prior_margin = values["GrossProfit"]["prior"] / values["Revenue"]["prior"] * 100
        changes.append(_build_change("GrossMarginPct", current_margin, prior_margin, is_ratio=True))

    return changes


def _build_change(metric_name: str, current: float, prior: float, is_ratio: bool = False) -> KPIChange:
    if prior == 0:
        pct_change = 0.0
    else:
        pct_change = (current - prior) / abs(prior) * 100

    # For a ratio like margin %, "unusual" is measured in percentage POINTS
    # moved, not percent change of the ratio itself (a move from 68.9% to
    # 67.9% is a 1.0 point move, not a meaningful "percent change of a
    # percent" figure).
    unusual_measure = abs(current - prior) if is_ratio else abs(pct_change)
    unusual = unusual_measure >= UNUSUAL_CHANGE_THRESHOLD_PCT

    return KPIChange(
        metric_name=metric_name,
        current_value=current,
        prior_value=prior,
        pct_change=round(pct_change, 1),
        unusual=unusual,
    )
