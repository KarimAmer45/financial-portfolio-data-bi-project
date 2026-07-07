"""Report visuals rendered with matplotlib.

Style rules used across all charts: single accent color for one measure,
largest value at the top, no chart junk, dollar axis in millions/billions.
"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter

from .insights import money_short

logger = logging.getLogger(__name__)

BAR_COLOR = "#31689b"
EMPHASIS_COLOR = "#1f4e79"
TITLE_COLOR = "#1a2733"
SUBTLE_COLOR = "#5b6b7a"
GRID_COLOR = "#d7dde3"

plt.rcParams.update(
    {
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "font.size": 11,
        "axes.titlesize": 11,
        "text.color": TITLE_COLOR,
        "axes.labelcolor": SUBTLE_COLOR,
        "xtick.color": SUBTLE_COLOR,
        "ytick.color": TITLE_COLOR,
    }
)


def _dollar_axis(ax) -> None:
    upper = ax.get_xlim()[1]
    if upper >= 2_000_000_000:
        formatter = FuncFormatter(lambda v, _: "0" if v == 0 else f"${v / 1e9:g}B")
    else:
        formatter = FuncFormatter(lambda v, _: "0" if v == 0 else f"${v / 1e6:g}M")
    ax.xaxis.set_major_formatter(formatter)


def _strip_axes(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID_COLOR)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)


def _titles(fig, title: str, subtitle: str) -> None:
    fig.text(0.06, 0.945, title, fontsize=17, fontweight="bold", color=TITLE_COLOR)
    fig.text(0.06, 0.905, subtitle, fontsize=11, color=SUBTLE_COLOR)


def _shorten(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _ranked_barh(
    labels: list[str],
    values: list[float],
    notes: list[str],
    title: str,
    subtitle: str,
    path: Path,
) -> None:
    """Horizontal bar chart, sorted with the largest value at the top."""
    order = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]
    notes = [notes[i] for i in order]

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.24, right=0.86, top=0.85, bottom=0.08)

    positions = range(len(values))
    colors = [EMPHASIS_COLOR if i == 0 else BAR_COLOR for i in range(len(values))]
    ax.barh(positions, values, height=0.62, color=colors)
    ax.set_yticks(positions)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()  # largest at the top
    ax.set_xlim(0, max(values) * 1.16)

    for pos, value, note in zip(positions, values, notes):
        ax.text(value + max(values) * 0.012, pos - 0.16, money_short(value),
                fontsize=11, fontweight="bold", color=TITLE_COLOR, va="center")
        ax.text(value + max(values) * 0.012, pos + 0.20, note,
                fontsize=8.5, color=SUBTLE_COLOR, va="center")

    _strip_axes(ax)
    _dollar_axis(ax)
    _titles(fig, title, subtitle)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    logger.info("Wrote %s", path.name)


def save_top_lenders(top_lenders: pd.DataFrame, path: Path) -> None:
    data = top_lenders.head(10)
    _ranked_barh(
        labels=[_shorten(row["lender"], 34) for _, row in data.iterrows()],
        values=[float(v) for v in data["approved_dollars"]],
        notes=[
            f"{row['market_share_pct']:.1f}% share, {int(row['approved_loans']):,} loans"
            for _, row in data.iterrows()
        ],
        title="Top 10 SBA 7(a) Lenders by Approved Dollars",
        subtitle="FY2024, all approval activity reported by the SBA",
        path=path,
    )


def save_top_states(project_states: pd.DataFrame, path: Path) -> None:
    data = project_states.head(10)
    _ranked_barh(
        labels=list(data["project_state"]),
        values=[float(v) for v in data["approved_dollars"]],
        notes=[
            f"{row['exposure_share_pct']:.1f}% share, {int(row['approved_loans']):,} loans"
            for _, row in data.iterrows()
        ],
        title="Top Project States by Approved Dollars",
        subtitle="FY2024, by business project location",
        path=path,
    )


def save_top_districts(districts: pd.DataFrame, path: Path) -> None:
    data = districts.head(10)
    _ranked_barh(
        labels=[_shorten(str(row["sba_do_name"]).title(), 34) for _, row in data.iterrows()],
        values=[float(v) for v in data["approved_dollars"]],
        notes=[
            f"{int(row['approved_loans']):,} loans, {row['guaranty_rate_pct']:.1f}% guaranty"
            for _, row in data.iterrows()
        ],
        title="Top SBA District Offices by Approved Dollars",
        subtitle="FY2024 district office activity view",
        path=path,
    )


def save_kpi_summary(kpi: pd.Series, path: Path) -> None:
    metrics = [
        ("Approved dollars", money_short(kpi["approved_dollars"])),
        ("Approved loans", f"{int(kpi['approved_loans']):,}"),
        ("Active lenders", f"{int(kpi['lender_count']):,}"),
        ("SBA guaranty", money_short(kpi["approved_sba_guaranty_dollars"])),
        ("Guaranty rate", f"{kpi['guaranty_rate_pct']:.1f}%"),
        ("Avg loan size", money_short(kpi["avg_loan_size"])),
        ("Project states", f"{int(kpi['project_state_count'])}"),
        ("Top 10 lender share", f"{kpi['top_10_lender_share_pct']:.1f}%"),
    ]

    fig = plt.figure(figsize=(12.8, 6.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.05, 0.90, "SBA 7(a) Lending Activity, FY2024", fontsize=19,
             fontweight="bold", color=TITLE_COLOR)
    fig.text(0.05, 0.845, "Year-end totals from the SBA lender activity report",
             fontsize=11.5, color=SUBTLE_COLOR)

    card_w, card_h = 0.205, 0.255
    gap_x, gap_y = 0.026, 0.055
    start_x, start_y = 0.05, 0.50
    for index, (label, value) in enumerate(metrics):
        row, col = divmod(index, 4)
        x = start_x + col * (card_w + gap_x)
        y = start_y - row * (card_h + gap_y)
        ax.add_patch(FancyBboxPatch(
            (x, y), card_w, card_h,
            boxstyle="round,pad=0.008,rounding_size=0.012",
            facecolor="#f4f6f9", edgecolor="#dbe2ea", linewidth=1,
        ))
        ax.plot([x + 0.004, x + 0.052], [y + card_h - 0.004] * 2,
                color=EMPHASIS_COLOR, linewidth=3, solid_capstyle="butt")
        ax.text(x + 0.016, y + card_h - 0.075, label, fontsize=11, color=SUBTLE_COLOR)
        ax.text(x + 0.016, y + 0.06, value, fontsize=21, fontweight="bold", color=TITLE_COLOR)

    fig.text(0.05, 0.045, "Source: U.S. Small Business Administration Open Data, 7(a) activity report FY2024.",
             fontsize=9.5, color=SUBTLE_COLOR)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    logger.info("Wrote %s", path.name)


def save_lender_concentration(lender_activity: pd.DataFrame, path: Path) -> None:
    """Cumulative share of approved dollars held by the top N lenders."""
    dollars = lender_activity["approved_dollars"].sort_values(ascending=False).reset_index(drop=True)
    total = dollars.sum()
    top_n = 50
    cumulative = (dollars.head(top_n).cumsum() / total * 100).tolist()
    ranks = list(range(1, len(cumulative) + 1))

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.09, right=0.95, top=0.85, bottom=0.11)

    ax.plot(ranks, cumulative, color=EMPHASIS_COLOR, linewidth=2.2)
    ax.fill_between(ranks, cumulative, color=EMPHASIS_COLOR, alpha=0.08)

    share_10 = cumulative[9]
    ax.scatter([10], [share_10], color=EMPHASIS_COLOR, zorder=3, s=36)
    ax.annotate(
        f"Top 10 lenders: {share_10:.1f}% of approved dollars",
        xy=(10, share_10), xytext=(14, share_10 - 7.5),
        fontsize=11, color=TITLE_COLOR,
        arrowprops={"arrowstyle": "-", "color": SUBTLE_COLOR, "linewidth": 0.9},
    )

    ax.set_xlim(1, top_n)
    ax.set_ylim(0, max(cumulative) * 1.15)
    ax.set_xlabel("Lender rank by approved dollars")
    ax.set_ylabel("")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID_COLOR)
    ax.tick_params(length=0)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)

    _titles(
        fig,
        "Lender Concentration, Cumulative Share of Approved Dollars",
        f"FY2024, {len(lender_activity):,} active lenders in total",
    )
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    logger.info("Wrote %s", path.name)


def export_visuals(
    analysis_tables: dict[str, pd.DataFrame],
    tables: dict[str, pd.DataFrame],
    visuals_dir: Path,
) -> None:
    visuals_dir.mkdir(exist_ok=True)
    save_kpi_summary(analysis_tables["kpi_summary"].iloc[0], visuals_dir / "kpi_summary.png")
    save_top_lenders(analysis_tables["top_lenders"], visuals_dir / "top_lenders.png")
    save_top_states(analysis_tables["project_state_activity"], visuals_dir / "top_project_states.png")
    save_top_districts(analysis_tables["district_office_activity"], visuals_dir / "top_district_offices.png")
    save_lender_concentration(tables["sba_lender_activity"], visuals_dir / "lender_concentration.png")
