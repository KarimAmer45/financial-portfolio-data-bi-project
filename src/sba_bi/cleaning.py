"""Load the raw SBA workbook and standardize each activity sheet."""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def snake_case(value: object) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def normalize_columns(raw_df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    df = raw_df.rename(columns=column_map).copy()
    df.columns = [snake_case(column) for column in df.columns]
    return df


def clean_activity_frame(
    raw_df: pd.DataFrame,
    required_text: list[str],
    column_map: dict[str, str],
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Clean one workbook sheet.

    Returns the cleaned frame, a log of row counts, and any rejected rows
    tagged with a rejection reason so they can be reviewed later.
    """
    rows_before = len(raw_df)
    df = raw_df.dropna(how="all").copy()
    rows_after_blank_drop = len(df)
    df = normalize_columns(df, column_map)

    for column in required_text:
        df[column] = df[column].astype("string").str.strip()
    for column in config.NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_before = df[required_text + config.NUMERIC_COLUMNS].isna().sum()

    # Rows missing a required field are rejected, not silently dropped.
    invalid_mask = df[required_text + config.NUMERIC_COLUMNS].isna().any(axis=1)
    rejected = df.loc[invalid_mask].copy()
    if not rejected.empty:
        rejected.insert(0, "rejection_reason", "missing_required_value")
    df = df.dropna(subset=required_text + config.NUMERIC_COLUMNS).copy()

    # Zero or negative loan counts / dollars are not valid activity rows.
    bad_amount_mask = (df["approved_loans"] <= 0) | (df["approved_dollars"] <= 0)
    bad_amounts = df.loc[bad_amount_mask].copy()
    if not bad_amounts.empty:
        bad_amounts.insert(0, "rejection_reason", "invalid_amount")
        rejected = pd.concat([rejected, bad_amounts], ignore_index=True)
    df = df[~bad_amount_mask].copy()

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
    return df, log, rejected


def load_and_clean_source() -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    """Read every configured sheet from the raw workbook and clean it."""
    if not config.RAW_PATH.exists():
        raise FileNotFoundError(f"Raw SBA workbook not found: {config.RAW_PATH}")

    sheet_config = config.load_sheet_config()
    tables: dict[str, pd.DataFrame] = {}
    cleaning_log: dict[str, dict] = {}
    rejected_frames: list[pd.DataFrame] = []

    for table_name, table_config in sheet_config.items():
        logger.info("Loading sheet %s -> %s", table_config["sheet"], table_name)
        raw_df = pd.read_excel(config.RAW_PATH, sheet_name=table_config["sheet"])
        clean_df, log, rejected = clean_activity_frame(
            raw_df,
            table_config["required_text"],
            table_config["columns"],
        )
        if not rejected.empty:
            rejected.insert(0, "source_table", table_name)
            rejected_frames.append(rejected)
        tables[table_name] = clean_df
        cleaning_log[table_name] = log
        logger.info(
            "%s: %s raw rows -> %s clean rows (%s removed)",
            table_name, log["raw_rows"], log["clean_rows"], log["rows_removed"],
        )

    if rejected_frames:
        tables["rejected_records"] = pd.concat(rejected_frames, ignore_index=True)
    else:
        tables["rejected_records"] = pd.DataFrame(
            columns=["source_table", "rejection_reason", "lender", "approved_loans", "approved_dollars"]
        )

    return tables, cleaning_log


def export_clean_csvs(tables: dict[str, pd.DataFrame]) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, path in config.TABLE_EXPORTS.items():
        tables[table_name].to_csv(path, index=False, lineterminator="\n")
        logger.info("Wrote %s", path.relative_to(config.ROOT))
