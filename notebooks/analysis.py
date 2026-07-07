"""
SBA 7(a) Lender Activity Data & BI workflow.

This script uses an official SBA Open Data workbook as the raw source, cleans
the lender activity sheets, exports analysis-ready CSVs, runs SQL queries in
SQLite, and generates a small set of BI visuals.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "lender7aactivity_fy2024_20240930.xlsx"
CONFIG_PATH = ROOT / "config" / "column_mappings.json"
PROCESSED_DIR = ROOT / "data" / "processed"
WAREHOUSE_DIR = ROOT / "data" / "warehouse"
QUALITY_DIR = ROOT / "data" / "quality"
SQL_PATH = ROOT / "sql" / "analysis_queries.sql"
VISUALS_DIR = ROOT / "visuals"

SOURCE_NAME = "SBA 7(a) & 504 Activity Reports, FY2024 Year End"
SOURCE_URL = "https://web.data.sba.gov/en/dataset/7-a-504-activity-reports-fy2024-year-end"
REPORTING_PERIOD = "2024-09-30"
DATE_KEY = 20240930

TABLE_EXPORTS = {
    "sba_lender_activity": PROCESSED_DIR / "sba_7a_lender_activity_fy2024.csv",
    "sba_lender_county_activity": PROCESSED_DIR / "sba_7a_lender_county_activity_fy2024.csv",
    "sba_district_office_activity": PROCESSED_DIR / "sba_7a_district_office_activity_fy2024.csv",
}

WAREHOUSE_EXPORTS = {
    "fact_lending_activity": WAREHOUSE_DIR / "fact_lending_activity.csv",
    "dim_lender": WAREHOUSE_DIR / "dim_lender.csv",
    "dim_geography": WAREHOUSE_DIR / "dim_geography.csv",
    "dim_date": WAREHOUSE_DIR / "dim_date.csv",
}

QUALITY_EXPORTS = {
    "quality_report": QUALITY_DIR / "data_quality_report.csv",
    "rejected_records": QUALITY_DIR / "rejected_records.csv",
}

DEFAULT_SHEET_CONFIG = {
    "sba_lender_activity": {
        "sheet": "Lender",
        "required_text": ["lender", "lender_city", "lender_state"],
        "columns": {
            "Lender": "lender",
            "Lender City": "lender_city",
            "Lender State": "lender_state",
            "Approved Loans": "approved_loans",
            "Approved Dollars": "approved_dollars",
            "Approved SBA Guaranty Dollars": "approved_sba_guaranty_dollars",
        },
    },
    "sba_lender_county_activity": {
        "sheet": "Lender_ProjCnty",
        "required_text": ["lender", "lender_city", "lender_state", "project_state", "project_county"],
        "columns": {
            "Lender": "lender",
            "Lender City": "lender_city",
            "Lender State": "lender_state",
            "Project State": "project_state",
            "Project County": "project_county",
            "Approved Loans": "approved_loans",
            "Approved Dollars": "approved_dollars",
            "Approved SBA Guaranty Dollars": "approved_sba_guaranty_dollars",
        },
    },
    "sba_district_office_activity": {
        "sheet": "Lender_DO",
        "required_text": ["lender", "lender_city", "lender_state", "do_code", "sba_do_name"],
        "columns": {
            "Lender": "lender",
            "Lender City": "lender_city",
            "Lender State": "lender_state",
            "DO Code": "do_code",
            "SBA DO Name": "sba_do_name",
            "Approved Loans": "approved_loans",
            "Approved Dollars": "approved_dollars",
            "Approved SBA Guaranty Dollars": "approved_sba_guaranty_dollars",
        },
    },
}

NUMERIC_COLUMNS = ["approved_loans", "approved_dollars", "approved_sba_guaranty_dollars"]
CHART_COLORS = ["#1F77B4", "#2CA58D", "#F28E2B", "#E15759", "#7B61FF", "#4E79A7"]
VALID_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR", "GU", "VI", "AS", "MP",
}

STATE_REGION = {
    "CT": "Northeast", "ME": "Northeast", "MA": "Northeast", "NH": "Northeast",
    "RI": "Northeast", "VT": "Northeast", "NJ": "Northeast", "NY": "Northeast",
    "PA": "Northeast",
    "IL": "Midwest", "IN": "Midwest", "MI": "Midwest", "OH": "Midwest",
    "WI": "Midwest", "IA": "Midwest", "KS": "Midwest", "MN": "Midwest",
    "MO": "Midwest", "NE": "Midwest", "ND": "Midwest", "SD": "Midwest",
    "DE": "South", "DC": "South", "FL": "South", "GA": "South", "MD": "South",
    "NC": "South", "SC": "South", "VA": "South", "WV": "South", "AL": "South",
    "KY": "South", "MS": "South", "TN": "South", "AR": "South", "LA": "South",
    "OK": "South", "TX": "South",
    "AZ": "West", "CO": "West", "ID": "West", "MT": "West", "NV": "West",
    "NM": "West", "UT": "West", "WY": "West", "AK": "West", "CA": "West",
    "HI": "West", "OR": "West", "WA": "West",
    "PR": "Territory", "GU": "Territory", "VI": "Territory", "AS": "Territory",
    "MP": "Territory",
}


def snake_case(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def load_column_config() -> dict[str, dict[str, object]]:
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return config["tables"]
    return DEFAULT_SHEET_CONFIG


def normalize_columns(raw_df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    df = raw_df.rename(columns=column_map).copy()
    df.columns = [snake_case(column) for column in df.columns]
    return df


def clean_activity_frame(
    raw_df: pd.DataFrame,
    required_text: list[str],
    column_map: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame]:
    """Standardize one SBA workbook sheet into an analysis-ready table."""
    rows_before = len(raw_df)
    df = raw_df.dropna(how="all").copy()
    rows_after_blank_drop = len(df)
    df = normalize_columns(df, column_map)

    for column in required_text:
        df[column] = df[column].astype("string").str.strip()

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_before = df[required_text + NUMERIC_COLUMNS].isna().sum()
    invalid_mask = df[required_text + NUMERIC_COLUMNS].isna().any(axis=1)
    rejected_records = df.loc[invalid_mask].copy()
    if not rejected_records.empty:
        rejected_records.insert(0, "rejection_reason", "missing_required_value")

    df = df.dropna(subset=required_text + NUMERIC_COLUMNS).copy()
    invalid_amount_mask = (df["approved_loans"] <= 0) | (df["approved_dollars"] <= 0)
    invalid_amount_records = df.loc[invalid_amount_mask].copy()
    if not invalid_amount_records.empty:
        invalid_amount_records.insert(0, "rejection_reason", "invalid_amount")
        rejected_records = pd.concat([rejected_records, invalid_amount_records], ignore_index=True)
    df = df[~invalid_amount_mask].copy()

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
    return df, log, rejected_records


def load_and_clean_source() -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, object]]]:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw SBA workbook not found: {RAW_PATH}")

    sheet_config = load_column_config()
    tables: dict[str, pd.DataFrame] = {}
    cleaning_log: dict[str, dict[str, object]] = {}
    rejected_frames: list[pd.DataFrame] = []
    for table_name, config in sheet_config.items():
        raw_df = pd.read_excel(RAW_PATH, sheet_name=config["sheet"])
        clean_df, log, rejected_records = clean_activity_frame(
            raw_df,
            config["required_text"],
            config["columns"],
        )
        if not rejected_records.empty:
            rejected_records.insert(0, "source_table", table_name)
            rejected_frames.append(rejected_records)
        tables[table_name] = clean_df
        cleaning_log[table_name] = log

    if rejected_frames:
        tables["rejected_records"] = pd.concat(rejected_frames, ignore_index=True)
    else:
        tables["rejected_records"] = pd.DataFrame(
            columns=["source_table", "rejection_reason", "lender", "approved_loans", "approved_dollars"]
        )

    return tables, cleaning_log


def export_clean_csvs(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, path in TABLE_EXPORTS.items():
        tables[table_name].to_csv(path, index=False)


def build_star_schema(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    lender_activity = tables["sba_lender_activity"]
    county_activity = tables["sba_lender_county_activity"]

    dim_lender = (
        lender_activity[["lender", "lender_city", "lender_state"]]
        .drop_duplicates()
        .sort_values(["lender", "lender_city", "lender_state"])
        .reset_index(drop=True)
    )
    dim_lender.insert(0, "lender_key", dim_lender.index + 1)
    dim_lender = dim_lender.rename(columns={"lender": "lender_name"})

    dim_geography = (
        county_activity[["project_state", "project_county"]]
        .drop_duplicates()
        .sort_values(["project_state", "project_county"])
        .reset_index(drop=True)
    )
    dim_geography.insert(0, "geography_key", dim_geography.index + 1)
    dim_geography = dim_geography.rename(columns={"project_state": "state", "project_county": "county"})
    dim_geography["district"] = "Not provided at county grain"
    dim_geography["region"] = dim_geography["state"].map(STATE_REGION).fillna("Unknown")

    dim_date = pd.DataFrame(
        [
            {
                "date_key": DATE_KEY,
                "reporting_period": REPORTING_PERIOD,
                "year": 2024,
                "quarter": "Q4",
                "month": 9,
                "period_label": "FY2024 Year End",
            }
        ]
    )

    fact = county_activity.merge(
        dim_lender,
        left_on=["lender", "lender_city", "lender_state"],
        right_on=["lender_name", "lender_city", "lender_state"],
        how="left",
        validate="many_to_one",
    ).merge(
        dim_geography,
        left_on=["project_state", "project_county"],
        right_on=["state", "county"],
        how="left",
        validate="many_to_one",
    )
    fact["date_key"] = DATE_KEY
    fact["reporting_period"] = REPORTING_PERIOD
    fact = fact.rename(
        columns={
            "approved_loans": "approved_loan_count",
            "approved_sba_guaranty_dollars": "guaranty_dollars",
        }
    )
    fact = fact[
        [
            "lender_key",
            "geography_key",
            "date_key",
            "reporting_period",
            "approved_loan_count",
            "approved_dollars",
            "guaranty_dollars",
        ]
    ]

    return {
        "fact_lending_activity": fact,
        "dim_lender": dim_lender,
        "dim_geography": dim_geography,
        "dim_date": dim_date,
    }


def export_warehouse_csvs(warehouse_tables: dict[str, pd.DataFrame]) -> None:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, path in WAREHOUSE_EXPORTS.items():
        warehouse_tables[table_name].to_csv(path, index=False)


def add_quality_check(checks: list[dict[str, object]], check_name: str, failed_count: int, details: str) -> None:
    checks.append(
        {
            "check_name": check_name,
            "status": "pass" if failed_count == 0 else "fail",
            "failed_count": int(failed_count),
            "details": details,
        }
    )


def run_quality_checks(
    tables: dict[str, pd.DataFrame],
    warehouse_tables: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    checks: list[dict[str, object]] = []
    rejected_records = tables["rejected_records"].copy()

    for table_name, table_df in tables.items():
        if table_name == "rejected_records":
            continue
        add_quality_check(
            checks,
            f"{table_name}_missing_required_values",
            int(table_df.isna().sum().sum()),
            "No nulls expected after cleaning selected SBA source sheets.",
        )
        add_quality_check(
            checks,
            f"{table_name}_duplicate_rows",
            int(table_df.duplicated().sum()),
            "Exact duplicate source rows should not appear after cleaning.",
        )
        add_quality_check(
            checks,
            f"{table_name}_non_negative_amounts",
            int(((table_df["approved_loans"] < 0) | (table_df["approved_dollars"] < 0)).sum()),
            "Approved loans and dollars must be non-negative.",
        )
        add_quality_check(
            checks,
            f"{table_name}_guaranty_not_above_approved",
            int((table_df["approved_sba_guaranty_dollars"] > table_df["approved_dollars"]).sum()),
            "SBA guaranty dollars should not exceed approved dollars.",
        )

    fact = warehouse_tables["fact_lending_activity"]
    dim_lender = warehouse_tables["dim_lender"]
    dim_geography = warehouse_tables["dim_geography"]

    add_quality_check(
        checks,
        "dim_lender_unique_key",
        int(dim_lender["lender_key"].duplicated().sum()),
        "Each lender dimension key must be unique.",
    )
    add_quality_check(
        checks,
        "dim_geography_unique_key",
        int(dim_geography["geography_key"].duplicated().sum()),
        "Each geography dimension key must be unique.",
    )
    add_quality_check(
        checks,
        "fact_lender_key_not_null",
        int(fact["lender_key"].isna().sum()),
        "Every fact row must match DimLender.",
    )
    add_quality_check(
        checks,
        "fact_geography_key_not_null",
        int(fact["geography_key"].isna().sum()),
        "Every fact row must match DimGeography.",
    )
    add_quality_check(
        checks,
        "dim_geography_valid_state_codes",
        int((~dim_geography["state"].isin(VALID_STATE_CODES)).sum()),
        "Project states should map to valid U.S. state or territory codes.",
    )
    add_quality_check(
        checks,
        "fact_non_negative_amounts",
        int(((fact["approved_loan_count"] < 0) | (fact["approved_dollars"] < 0) | (fact["guaranty_dollars"] < 0)).sum()),
        "Fact table financial fields must be non-negative.",
    )
    add_quality_check(
        checks,
        "fact_guaranty_not_above_approved",
        int((fact["guaranty_dollars"] > fact["approved_dollars"]).sum()),
        "Fact guaranty dollars should not exceed approved dollars.",
    )

    quality_report = pd.DataFrame(checks)
    return quality_report, rejected_records


def export_quality_outputs(quality_report: pd.DataFrame, rejected_records: pd.DataFrame) -> None:
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    quality_report.to_csv(QUALITY_EXPORTS["quality_report"], index=False)
    rejected_records.to_csv(QUALITY_EXPORTS["rejected_records"], index=False)


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
    warehouse_tables = build_star_schema(tables)
    export_warehouse_csvs(warehouse_tables)
    quality_report, rejected_records = run_quality_checks(tables, warehouse_tables)
    export_quality_outputs(quality_report, rejected_records)
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

    print("Data-quality summary")
    print(quality_report.to_string(index=False))
    print(f"Rejected records: {len(rejected_records):,}")
    print()

    print("Business insights")
    for insight in insights:
        print(f"- {insight}")
    print()

    print("Cleaned CSV exports")
    for path in TABLE_EXPORTS.values():
        print(f"- {path}")
    print("Warehouse CSV exports")
    for path in WAREHOUSE_EXPORTS.values():
        print(f"- {path}")
    print("Quality exports")
    for path in QUALITY_EXPORTS.values():
        print(f"- {path}")
    print(f"Visuals saved to: {VISUALS_DIR}")


if __name__ == "__main__":
    main()
