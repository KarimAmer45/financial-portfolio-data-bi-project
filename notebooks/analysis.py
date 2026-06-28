"""
SBA 7(a) Lender Activity Data & BI workflow.

This script uses an official SBA Open Data workbook as the raw source, cleans
the lender activity sheets, exports analysis-ready CSVs, runs SQL queries in
SQLite, and generates a small set of BI visuals.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "lender7aactivity_fy2024_20240930.xlsx"
PROCESSED_DIR = ROOT / "data" / "processed"
SQL_PATH = ROOT / "sql" / "analysis_queries.sql"
VISUALS_DIR = ROOT / "visuals"

SOURCE_NAME = "SBA 7(a) & 504 Activity Reports, FY2024 Year End"
SOURCE_URL = "https://web.data.sba.gov/en/dataset/7-a-504-activity-reports-fy2024-year-end"

TABLE_EXPORTS = {
    "sba_lender_activity": PROCESSED_DIR / "sba_7a_lender_activity_fy2024.csv",
    "sba_lender_county_activity": PROCESSED_DIR / "sba_7a_lender_county_activity_fy2024.csv",
    "sba_district_office_activity": PROCESSED_DIR / "sba_7a_district_office_activity_fy2024.csv",
}

SHEET_CONFIG = {
    "sba_lender_activity": {
        "sheet": "Lender",
        "required_text": ["lender", "lender_city", "lender_state"],
    },
    "sba_lender_county_activity": {
        "sheet": "Lender_ProjCnty",
        "required_text": ["lender", "lender_city", "lender_state", "project_state", "project_county"],
    },
    "sba_district_office_activity": {
        "sheet": "Lender_DO",
        "required_text": ["lender", "lender_city", "lender_state", "do_code", "sba_do_name"],
    },
}

NUMERIC_COLUMNS = ["approved_loans", "approved_dollars", "approved_sba_guaranty_dollars"]
CHART_COLORS = ["#1F77B4", "#2CA58D", "#F28E2B", "#E15759", "#7B61FF", "#4E79A7"]


def snake_case(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def clean_activity_frame(raw_df: pd.DataFrame, required_text: list[str]) -> tuple[pd.DataFrame, dict[str, object]]:
    """Standardize one SBA workbook sheet into an analysis-ready table."""
    rows_before = len(raw_df)
    df = raw_df.dropna(how="all").copy()
    rows_after_blank_drop = len(df)
    df.columns = [snake_case(column) for column in df.columns]

    for column in required_text:
        df[column] = df[column].astype("string").str.strip()

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_before = df[required_text + NUMERIC_COLUMNS].isna().sum()
    df = df.dropna(subset=required_text + NUMERIC_COLUMNS).copy()
    df = df[(df["approved_loans"] > 0) & (df["approved_dollars"] > 0)].copy()

    df["approved_loans"] = df["approved_loans"].round(0).astype(int)
    df["approved_dollars"] = df["approved_dollars"].round(2)
    df["approved_sba_guaranty_dollars"] = df["approved_sba_guaranty_dollars"].round(2)
    df["avg_loan_size"] = (df["approved_dollars"] / df["approved_loans"]).round(2)
    df["guaranty_rate_pct"] = (
        100 * df["approved_sba_guaranty_dollars"] / df["approved_dollars"]
    ).replace([np.inf, -np.inf], np.nan).round(2)

    log = {
        "raw_rows": rows_before,
        "rows_after_blank_drop": rows_after_blank_drop,
        "clean_rows": len(df),
        "rows_removed": rows_before - len(df),
        "missing_before": missing_before[missing_before > 0].to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }
    return df, log


def load_and_clean_source() -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, object]]]:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw SBA workbook not found: {RAW_PATH}")

    tables: dict[str, pd.DataFrame] = {}
    cleaning_log: dict[str, dict[str, object]] = {}
    for table_name, config in SHEET_CONFIG.items():
        raw_df = pd.read_excel(RAW_PATH, sheet_name=config["sheet"])
        clean_df, log = clean_activity_frame(raw_df, config["required_text"])
        tables[table_name] = clean_df
        cleaning_log[table_name] = log

    return tables, cleaning_log


def export_clean_csvs(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, path in TABLE_EXPORTS.items():
        tables[table_name].to_csv(path, index=False)


def load_named_queries(path: Path) -> dict[str, str]:
    queries: dict[str, list[str]] = {}
    current_name: str | None = None

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("-- name:"):
            current_name = line.split(":", 1)[1].strip()
            queries[current_name] = []
        elif current_name:
            queries[current_name].append(line)

    return {name: "\n".join(lines).strip().rstrip(";") for name, lines in queries.items()}


def run_sql_analysis(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    queries = load_named_queries(SQL_PATH)
    with sqlite3.connect(":memory:") as connection:
        for table_name, table_df in tables.items():
            table_df.to_sql(table_name, connection, if_exists="replace", index=False)
        return {name: pd.read_sql_query(query, connection) for name, query in queries.items()}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "segoeuib.ttf" if bold else "segoeui.ttf"]
    for name in font_names:
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int = 24,
    fill: str = "#1F2937",
    bold: bool = False,
    anchor: str | None = None,
) -> None:
    draw.text(xy, text, font=font(size, bold=bold), fill=fill, anchor=anchor)


def text_width(draw: ImageDraw.ImageDraw, text: str, size: int, bold: bool = False) -> int:
    bbox = draw.textbbox((0, 0), text, font=font(size, bold=bold))
    return bbox[2] - bbox[0]


def truncate_text(draw: ImageDraw.ImageDraw, text: str, size: int, max_width: int, bold: bool = False) -> str:
    if text_width(draw, text, size, bold) <= max_width:
        return text
    suffix = "..."
    trimmed = text
    while trimmed and text_width(draw, trimmed + suffix, size, bold) > max_width:
        trimmed = trimmed[:-1]
    return trimmed.rstrip() + suffix


def money_short(value: float) -> str:
    value = float(value)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def save_kpi_summary(kpi: pd.Series, path: Path) -> None:
    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#F6F7F9")
    draw = ImageDraw.Draw(image)

    draw_text(draw, (64, 52), "SBA 7(a) Lender Activity KPI Summary", 40, "#111827", bold=True)
    draw_text(draw, (66, 106), "FY2024 public SBA lender activity workbook", 23, "#4B5563")

    metrics = [
        ("Approved dollars", money_short(kpi["approved_dollars"]), "#1F77B4"),
        ("Approved loans", f"{int(kpi['approved_loans']):,}", "#2CA58D"),
        ("Active lenders", f"{int(kpi['lender_count']):,}", "#F28E2B"),
        ("SBA guaranty", money_short(kpi["approved_sba_guaranty_dollars"]), "#7B61FF"),
        ("Guaranty rate", f"{kpi['guaranty_rate_pct']:.2f}%", "#E15759"),
        ("Avg loan size", money_short(kpi["avg_loan_size"]), "#B07AA1"),
        ("Project states", f"{int(kpi['project_state_count']):,}", "#59A14F"),
        ("Top 10 lender share", f"{kpi['top_10_lender_share_pct']:.2f}%", "#EDC948"),
    ]

    card_w, card_h = 300, 190
    start_x, start_y = 64, 185
    gap_x, gap_y = 32, 36
    for index, (label, value, accent) in enumerate(metrics):
        row, col = divmod(index, 4)
        x = start_x + col * (card_w + gap_x)
        y = start_y + row * (card_h + gap_y)
        draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=10, fill="#FFFFFF", outline="#D9DEE8", width=2)
        draw.rounded_rectangle((x, y, x + 12, y + card_h), radius=10, fill=accent)
        draw_text(draw, (x + 34, y + 34), label, 23, "#4B5563")
        draw_text(draw, (x + 34, y + 92), value, 37, "#111827", bold=True)

    footer = "Source: U.S. Small Business Administration Open Data, FY2024 7(a) lender activity."
    draw_text(draw, (64, 765), footer, 21, "#4B5563")
    image.save(path)


def save_top_lenders(top_lenders: pd.DataFrame, path: Path) -> None:
    data = top_lenders.head(10).sort_values("approved_dollars", ascending=True).reset_index(drop=True)
    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)

    draw_text(draw, (64, 52), "Top SBA 7(a) Lenders by Approved Dollars", 38, "#111827", bold=True)
    draw_text(draw, (66, 104), "FY2024 lender concentration and market share", 23, "#4B5563")

    left, top, bar_w, bar_h, gap = 430, 168, 690, 48, 18
    max_value = float(data["approved_dollars"].max())

    for idx, row in data.iterrows():
        y = top + idx * (bar_h + gap)
        value = float(row["approved_dollars"])
        fill_w = int((value / max_value) * bar_w)
        label = truncate_text(draw, str(row["lender"]), 21, 320, bold=True)
        location = f"{row['lender_city']}, {row['lender_state']}"
        draw_text(draw, (64, y + 2), label, 21, "#111827", bold=True)
        draw_text(draw, (64, y + 29), location, 16, "#6B7280")
        draw.rounded_rectangle((left, y, left + bar_w, y + bar_h), radius=7, fill="#EEF2F7")
        draw.rounded_rectangle((left, y, left + fill_w, y + bar_h), radius=7, fill=CHART_COLORS[idx % len(CHART_COLORS)])
        draw_text(draw, (left + fill_w + 16, y + 1), money_short(value), 22, "#111827", bold=True)
        context = f"{row['market_share_pct']:.1f}% share | {int(row['approved_loans']):,} loans"
        draw_text(draw, (left + fill_w + 16, y + 28), context, 16, "#4B5563")

    image.save(path)


def save_top_states(project_states: pd.DataFrame, path: Path) -> None:
    data = project_states.head(10).sort_values("approved_dollars", ascending=True).reset_index(drop=True)
    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)

    draw_text(draw, (64, 52), "Top Project States by SBA Approved Dollars", 38, "#111827", bold=True)
    draw_text(draw, (66, 104), "Geographic exposure based on business project location", 23, "#4B5563")

    left, top, bar_w, bar_h, gap = 170, 168, 870, 48, 18
    max_value = float(data["approved_dollars"].max())

    for idx, row in data.iterrows():
        y = top + idx * (bar_h + gap)
        value = float(row["approved_dollars"])
        fill_w = int((value / max_value) * bar_w)
        draw_text(draw, (64, y + 11), str(row["project_state"]), 26, "#111827", bold=True)
        draw.rounded_rectangle((left, y, left + bar_w, y + bar_h), radius=7, fill="#EEF2F7")
        draw.rounded_rectangle((left, y, left + fill_w, y + bar_h), radius=7, fill=CHART_COLORS[idx % len(CHART_COLORS)])
        draw_text(draw, (left + fill_w + 16, y + 1), money_short(value), 22, "#111827", bold=True)
        context = f"{row['exposure_share_pct']:.1f}% share | {int(row['approved_loans']):,} loans"
        draw_text(draw, (left + fill_w + 16, y + 28), context, 16, "#4B5563")

    image.save(path)


def save_top_districts(districts: pd.DataFrame, path: Path) -> None:
    data = districts.head(10).sort_values("approved_dollars", ascending=True).reset_index(drop=True)
    width, height = 1400, 850
    image = Image.new("RGB", (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(image)

    draw_text(draw, (64, 52), "Top SBA District Offices by Approved Dollars", 38, "#111827", bold=True)
    draw_text(draw, (66, 104), "District office activity view from the SBA workbook", 23, "#4B5563")

    left, top, bar_w, bar_h, gap = 485, 168, 620, 48, 18
    max_value = float(data["approved_dollars"].max())

    for idx, row in data.iterrows():
        y = top + idx * (bar_h + gap)
        value = float(row["approved_dollars"])
        fill_w = int((value / max_value) * bar_w)
        label = truncate_text(draw, str(row["sba_do_name"]).title(), 20, 380, bold=True)
        draw_text(draw, (64, y + 11), label, 20, "#111827", bold=True)
        draw.rounded_rectangle((left, y, left + bar_w, y + bar_h), radius=7, fill="#EEF2F7")
        draw.rounded_rectangle((left, y, left + fill_w, y + bar_h), radius=7, fill=CHART_COLORS[idx % len(CHART_COLORS)])
        draw_text(draw, (left + fill_w + 16, y + 1), money_short(value), 22, "#111827", bold=True)
        context = f"{int(row['approved_loans']):,} loans | {row['guaranty_rate_pct']:.1f}% guaranty"
        draw_text(draw, (left + fill_w + 16, y + 28), context, 16, "#4B5563")

    image.save(path)


def export_visuals(tables: dict[str, pd.DataFrame]) -> None:
    VISUALS_DIR.mkdir(exist_ok=True)
    save_kpi_summary(tables["kpi_summary"].iloc[0], VISUALS_DIR / "kpi_summary.png")
    save_top_lenders(tables["top_lenders"], VISUALS_DIR / "top_lenders.png")
    save_top_states(tables["project_state_activity"], VISUALS_DIR / "top_project_states.png")
    save_top_districts(tables["district_office_activity"], VISUALS_DIR / "top_district_offices.png")


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
        f"SBA 7(a) FY2024 activity totals {money_short(kpi['approved_dollars'])} across {int(kpi['approved_loans']):,} approved loans and {int(kpi['lender_count']):,} lenders.",
        f"The SBA guaranty amount is {money_short(kpi['approved_sba_guaranty_dollars'])}, equal to {kpi['guaranty_rate_pct']:.2f}% of approved dollars.",
        f"The top 10 lenders account for {kpi['top_10_lender_share_pct']:.2f}% of approved dollars, so lender concentration is meaningful but not dominated by one lender.",
        f"{top_lender['lender']} is the largest lender by approved dollars at {money_short(top_lender['approved_dollars'])}, representing {top_lender['market_share_pct']:.2f}% of total activity.",
        f"{top_state['project_state']} is the largest project state at {money_short(top_state['approved_dollars'])}, representing {top_state['exposure_share_pct']:.2f}% of approved dollars.",
        f"{top_county['project_county']}, {top_county['project_state']} is the largest county exposure at {money_short(top_county['approved_dollars'])}.",
        f"{top_district['sba_do_name'].title()} is the largest SBA district office view at {money_short(top_district['approved_dollars'])}.",
        f"{top_reach['lender']} has the widest geographic reach among the top lenders, spanning {int(top_reach['project_states'])} project states and territories.",
    ]


def print_cleaning_summary(cleaning_log: dict[str, dict[str, object]]) -> None:
    print("Cleaning summary")
    for table_name, log in cleaning_log.items():
        print(f"- {table_name}:")
        print(f"  raw rows: {log['raw_rows']:,}")
        print(f"  clean rows: {log['clean_rows']:,}")
        print(f"  rows removed: {log['rows_removed']:,}")
        print(f"  missing before: {log['missing_before']}")
        print(f"  duplicate rows after cleaning: {log['duplicate_rows']:,}")
    print()


def main() -> None:
    tables, cleaning_log = load_and_clean_source()
    export_clean_csvs(tables)
    analysis_tables = run_sql_analysis(tables)
    export_visuals(analysis_tables)
    insights = build_insights(analysis_tables)

    print(f"Source: {SOURCE_NAME}")
    print(f"Source URL: {SOURCE_URL}")
    print(f"Raw workbook: {RAW_PATH}")
    print()
    print_cleaning_summary(cleaning_log)

    print("KPI summary")
    print(analysis_tables["kpi_summary"].to_string(index=False))
    print()

    print("Business insights")
    for insight in insights:
        print(f"- {insight}")
    print()

    print("Cleaned CSV exports")
    for path in TABLE_EXPORTS.values():
        print(f"- {path}")
    print(f"Visuals saved to: {VISUALS_DIR}")


if __name__ == "__main__":
    main()
