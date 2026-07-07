"""Build the star schema (fact + dimensions) from cleaned activity tables."""

from __future__ import annotations

import logging

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def build_star_schema(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Derive DimLender, DimGeography, DimDate and the county-grain fact table.

    The source workbook is aggregated lender activity, so the fact grain is
    lender x project county x reporting period. There is no loan-level detail
    to model below that.
    """
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
    dim_geography["region"] = dim_geography["state"].map(config.STATE_REGION).fillna("Unknown")

    dim_date = pd.DataFrame(
        [
            {
                "date_key": config.DATE_KEY,
                "reporting_period": config.REPORTING_PERIOD,
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
    fact["date_key"] = config.DATE_KEY
    fact["reporting_period"] = config.REPORTING_PERIOD
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

    logger.info(
        "Star schema: %s fact rows, %s lenders, %s geographies",
        len(fact), len(dim_lender), len(dim_geography),
    )
    return {
        "fact_lending_activity": fact,
        "dim_lender": dim_lender,
        "dim_geography": dim_geography,
        "dim_date": dim_date,
    }


def export_warehouse_csvs(warehouse_tables: dict[str, pd.DataFrame]) -> None:
    config.WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    for table_name, path in config.WAREHOUSE_EXPORTS.items():
        warehouse_tables[table_name].to_csv(path, index=False, lineterminator="\n")
        logger.info("Wrote %s", path.relative_to(config.ROOT))
