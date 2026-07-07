"""Unit tests for star-schema construction and quality checks on synthetic data."""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sba_bi.quality import run_quality_checks  # noqa: E402
from sba_bi.warehouse import build_star_schema  # noqa: E402


def make_tables():
    lender_activity = pd.DataFrame({
        "lender": ["First Bank", "Second Bank"],
        "lender_city": ["Austin", "Miami"],
        "lender_state": ["TX", "FL"],
        "approved_loans": [4, 2],
        "approved_dollars": [2_000_000.0, 500_000.0],
        "approved_sba_guaranty_dollars": [1_500_000.0, 375_000.0],
        "avg_loan_size": [500_000.0, 250_000.0],
        "guaranty_rate_pct": [75.0, 75.0],
    })
    county_activity = pd.DataFrame({
        "lender": ["First Bank", "First Bank", "Second Bank"],
        "lender_city": ["Austin", "Austin", "Miami"],
        "lender_state": ["TX", "TX", "FL"],
        "project_state": ["TX", "OK", "FL"],
        "project_county": ["TRAVIS", "TULSA", "MIAMI-DADE"],
        "approved_loans": [3, 1, 2],
        "approved_dollars": [1_500_000.0, 500_000.0, 500_000.0],
        "approved_sba_guaranty_dollars": [1_125_000.0, 375_000.0, 375_000.0],
        "avg_loan_size": [500_000.0, 500_000.0, 250_000.0],
        "guaranty_rate_pct": [75.0, 75.0, 75.0],
    })
    district_activity = pd.DataFrame({
        "lender": ["First Bank"],
        "lender_city": ["Austin"],
        "lender_state": ["TX"],
        "do_code": ["0651"],
        "sba_do_name": ["DALLAS / FT WORTH DISTRICT OFFICE"],
        "approved_loans": [4],
        "approved_dollars": [2_000_000.0],
        "approved_sba_guaranty_dollars": [1_500_000.0],
        "avg_loan_size": [500_000.0],
        "guaranty_rate_pct": [75.0],
    })
    return {
        "sba_lender_activity": lender_activity,
        "sba_lender_county_activity": county_activity,
        "sba_district_office_activity": district_activity,
        "rejected_records": pd.DataFrame(),
    }


class StarSchemaTests(unittest.TestCase):
    def setUp(self):
        self.tables = make_tables()
        self.warehouse = build_star_schema(self.tables)

    def test_dimension_keys_are_unique(self):
        self.assertFalse(self.warehouse["dim_lender"]["lender_key"].duplicated().any())
        self.assertFalse(self.warehouse["dim_geography"]["geography_key"].duplicated().any())

    def test_fact_foreign_keys_resolve(self):
        fact = self.warehouse["fact_lending_activity"]
        self.assertFalse(fact["lender_key"].isna().any())
        self.assertFalse(fact["geography_key"].isna().any())

    def test_fact_grain_and_totals_match_source(self):
        fact = self.warehouse["fact_lending_activity"]
        source = self.tables["sba_lender_county_activity"]
        self.assertEqual(len(fact), len(source))
        self.assertAlmostEqual(fact["approved_dollars"].sum(), source["approved_dollars"].sum())
        self.assertAlmostEqual(fact["guaranty_dollars"].sum(),
                               source["approved_sba_guaranty_dollars"].sum())

    def test_region_mapping(self):
        dim_geography = self.warehouse["dim_geography"]
        regions = dict(zip(dim_geography["state"], dim_geography["region"]))
        self.assertEqual(regions["TX"], "South")
        self.assertEqual(regions["OK"], "South")
        self.assertEqual(regions["FL"], "South")


class QualityCheckTests(unittest.TestCase):
    def test_all_checks_pass_on_clean_input(self):
        tables = make_tables()
        report, rejected = run_quality_checks(tables, build_star_schema(tables))
        self.assertTrue((report["status"] == "pass").all(), report.to_string(index=False))
        self.assertTrue(rejected.empty)

    def test_guaranty_above_approved_is_flagged(self):
        tables = make_tables()
        bad = tables["sba_lender_activity"].copy()
        bad.loc[0, "approved_sba_guaranty_dollars"] = bad.loc[0, "approved_dollars"] + 1
        tables["sba_lender_activity"] = bad

        report, _ = run_quality_checks(tables, build_star_schema(tables))
        check = report[report["check_name"] == "sba_lender_activity_guaranty_not_above_approved"]
        self.assertEqual(check.iloc[0]["status"], "fail")
        self.assertEqual(check.iloc[0]["failed_count"], 1)


if __name__ == "__main__":
    unittest.main()
