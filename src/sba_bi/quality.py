"""Data-quality checks over cleaned tables and the star schema."""

from __future__ import annotations

import logging

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def _add_check(checks: list[dict], check_name: str, failed_count: int, details: str) -> None:
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
    """Validate source tables and star schema. Returns (report, rejected rows)."""
    checks: list[dict] = []
    rejected_records = tables["rejected_records"].copy()

    for table_name, table_df in tables.items():
        if table_name == "rejected_records":
            continue
        _add_check(
            checks,
            f"{table_name}_missing_required_values",
            int(table_df.isna().sum().sum()),
            "No nulls expected after cleaning selected SBA source sheets.",
        )
        _add_check(
            checks,
            f"{table_name}_duplicate_rows",
            int(table_df.duplicated().sum()),
            "Exact duplicate source rows should not appear after cleaning.",
        )
        _add_check(
            checks,
            f"{table_name}_non_negative_amounts",
            int(((table_df["approved_loans"] < 0) | (table_df["approved_dollars"] < 0)).sum()),
            "Approved loans and dollars must be non-negative.",
        )
        _add_check(
            checks,
            f"{table_name}_guaranty_not_above_approved",
            int((table_df["approved_sba_guaranty_dollars"] > table_df["approved_dollars"]).sum()),
            "SBA guaranty dollars should not exceed approved dollars.",
        )

    fact = warehouse_tables["fact_lending_activity"]
    dim_lender = warehouse_tables["dim_lender"]
    dim_geography = warehouse_tables["dim_geography"]

    _add_check(
        checks,
        "dim_lender_unique_key",
        int(dim_lender["lender_key"].duplicated().sum()),
        "Each lender dimension key must be unique.",
    )
    _add_check(
        checks,
        "dim_geography_unique_key",
        int(dim_geography["geography_key"].duplicated().sum()),
        "Each geography dimension key must be unique.",
    )
    _add_check(
        checks,
        "fact_lender_key_not_null",
        int(fact["lender_key"].isna().sum()),
        "Every fact row must match DimLender.",
    )
    _add_check(
        checks,
        "fact_geography_key_not_null",
        int(fact["geography_key"].isna().sum()),
        "Every fact row must match DimGeography.",
    )
    _add_check(
        checks,
        "dim_geography_valid_state_codes",
        int((~dim_geography["state"].isin(config.VALID_STATE_CODES)).sum()),
        "Project states should map to valid U.S. state or territory codes.",
    )
    _add_check(
        checks,
        "fact_non_negative_amounts",
        int(
            (
                (fact["approved_loan_count"] < 0)
                | (fact["approved_dollars"] < 0)
                | (fact["guaranty_dollars"] < 0)
            ).sum()
        ),
        "Fact table financial fields must be non-negative.",
    )
    _add_check(
        checks,
        "fact_guaranty_not_above_approved",
        int((fact["guaranty_dollars"] > fact["approved_dollars"]).sum()),
        "Fact guaranty dollars should not exceed approved dollars.",
    )

    quality_report = pd.DataFrame(checks)
    failed = quality_report[quality_report["status"] != "pass"]
    if failed.empty:
        logger.info("Data quality: all %s checks passed", len(quality_report))
    else:
        logger.warning("Data quality: %s of %s checks FAILED", len(failed), len(quality_report))
    return quality_report, rejected_records


def export_quality_outputs(quality_report: pd.DataFrame, rejected_records: pd.DataFrame) -> None:
    config.QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    quality_report.to_csv(config.QUALITY_EXPORTS["quality_report"], index=False, lineterminator="\n")
    rejected_records.to_csv(config.QUALITY_EXPORTS["rejected_records"], index=False, lineterminator="\n")
    logger.info("Wrote data-quality report (%s rejected records)", len(rejected_records))
