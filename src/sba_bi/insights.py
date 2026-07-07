"""Formatting helpers and the headline business insights."""

from __future__ import annotations

import pandas as pd


def money_short(value: float) -> str:
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def build_insights(tables: dict[str, pd.DataFrame]) -> list[str]:
    kpi = tables["kpi_summary"].iloc[0]
    top_lender = tables["top_lenders"].iloc[0]
    top_state = tables["project_state_activity"].iloc[0]
    top_county = tables["county_concentration"].iloc[0]
    top_district = tables["district_office_activity"].iloc[0]
    top_reach = tables["lender_geographic_reach"].sort_values(
        ["project_states", "approved_dollars"], ascending=False
    ).iloc[0]

    return [
        f"SBA 7(a) FY2024 activity totals {money_short(kpi['approved_dollars'])} across "
        f"{int(kpi['approved_loans']):,} approved loans and {int(kpi['lender_count']):,} lenders.",
        f"The SBA guaranty amount is {money_short(kpi['approved_sba_guaranty_dollars'])}, "
        f"equal to {kpi['guaranty_rate_pct']:.2f}% of approved dollars.",
        f"The top 10 lenders account for {kpi['top_10_lender_share_pct']:.2f}% of approved dollars, "
        "so concentration is meaningful but no single lender dominates.",
        f"{top_lender['lender']} is the largest lender by approved dollars at "
        f"{money_short(top_lender['approved_dollars'])} ({top_lender['market_share_pct']:.2f}% of total).",
        f"{top_state['project_state']} is the largest project state at "
        f"{money_short(top_state['approved_dollars'])} ({top_state['exposure_share_pct']:.2f}% of approved dollars).",
        f"{top_county['project_county']}, {top_county['project_state']} is the largest county exposure at "
        f"{money_short(top_county['approved_dollars'])}.",
        f"{str(top_district['sba_do_name']).title()} is the largest SBA district office view at "
        f"{money_short(top_district['approved_dollars'])}.",
        f"{top_reach['lender']} has the widest geographic reach among top lenders, spanning "
        f"{int(top_reach['project_states'])} project states and territories.",
    ]
