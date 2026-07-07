"""Integration tests that run the cleaning and modeling steps on the real workbook."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sba_bi import cleaning, config, quality, warehouse  # noqa: E402


@unittest.skipUnless(config.RAW_PATH.exists(), "raw SBA workbook not present")
class PipelineOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, cls.cleaning_log = cleaning.load_and_clean_source()
        cls.warehouse_tables = warehouse.build_star_schema(cls.tables)
        cls.quality_report, cls.rejected_records = quality.run_quality_checks(
            cls.tables,
            cls.warehouse_tables,
        )

    def test_no_rejected_records(self):
        self.assertEqual(len(self.rejected_records), 0)

    def test_source_tables_are_clean(self):
        for table_name, table_df in self.tables.items():
            if table_name == "rejected_records":
                continue
            self.assertEqual(table_df.isna().sum().sum(), 0, table_name)
            self.assertEqual(table_df.duplicated().sum(), 0, table_name)

    def test_financial_amounts_are_valid(self):
        for table_name, table_df in self.tables.items():
            if table_name == "rejected_records":
                continue
            self.assertTrue((table_df["approved_loans"] > 0).all(), table_name)
            self.assertTrue((table_df["approved_dollars"] > 0).all(), table_name)
            self.assertTrue(
                (table_df["approved_sba_guaranty_dollars"] <= table_df["approved_dollars"]).all(),
                table_name,
            )

    def test_star_schema_keys_are_valid(self):
        fact = self.warehouse_tables["fact_lending_activity"]
        self.assertFalse(self.warehouse_tables["dim_lender"]["lender_key"].duplicated().any())
        self.assertFalse(self.warehouse_tables["dim_geography"]["geography_key"].duplicated().any())
        self.assertFalse(fact["lender_key"].isna().any())
        self.assertFalse(fact["geography_key"].isna().any())

    def test_fact_totals_reconcile_to_source(self):
        fact = self.warehouse_tables["fact_lending_activity"]
        source = self.tables["sba_lender_county_activity"]
        self.assertAlmostEqual(
            fact["approved_dollars"].sum(), source["approved_dollars"].sum(), places=2
        )
        self.assertEqual(int(fact["approved_loan_count"].sum()), int(source["approved_loans"].sum()))

    def test_all_quality_checks_pass(self):
        failed = self.quality_report[self.quality_report["status"] != "pass"]
        self.assertTrue(failed.empty, failed.to_string(index=False))


if __name__ == "__main__":
    unittest.main()
