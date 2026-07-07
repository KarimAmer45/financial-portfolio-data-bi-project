"""Run the full SBA 7(a) BI pipeline.

Usage:
    python src/run_pipeline.py [--skip-charts] [-v]

Reads the raw SBA workbook, cleans each activity sheet, exports processed
CSVs, builds the star schema, runs data-quality checks, executes the SQL
analysis queries, and renders the report visuals.
"""

from __future__ import annotations

import argparse
import logging

from sba_bi import charts, cleaning, config, insights, quality, sql_runner, warehouse

logger = logging.getLogger("sba_bi.pipeline")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SBA 7(a) lender activity BI pipeline")
    parser.add_argument("--skip-charts", action="store_true", help="skip rendering PNG visuals")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Source: %s", config.SOURCE_NAME)

    tables, _cleaning_log = cleaning.load_and_clean_source()
    cleaning.export_clean_csvs(tables)

    warehouse_tables = warehouse.build_star_schema(tables)
    warehouse.export_warehouse_csvs(warehouse_tables)

    quality_report, rejected_records = quality.run_quality_checks(tables, warehouse_tables)
    quality.export_quality_outputs(quality_report, rejected_records)

    analysis_tables = sql_runner.run_sql_analysis(tables)
    if not args.skip_charts:
        charts.export_visuals(analysis_tables, tables, config.VISUALS_DIR)

    kpi = analysis_tables["kpi_summary"].iloc[0]
    logger.info(
        "KPIs: %s approved across %s loans, guaranty rate %.2f%%, top-10 share %.2f%%",
        insights.money_short(kpi["approved_dollars"]),
        f"{int(kpi['approved_loans']):,}",
        kpi["guaranty_rate_pct"],
        kpi["top_10_lender_share_pct"],
    )
    for line in insights.build_insights(analysis_tables):
        logger.info("Insight: %s", line)

    failed = quality_report[quality_report["status"] != "pass"]
    if not failed.empty:
        logger.error("Failed data-quality checks:\n%s", failed.to_string(index=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
