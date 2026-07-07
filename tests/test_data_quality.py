import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))

import analysis  # noqa: E402


class DataQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables, cls.cleaning_log = analysis.load_and_clean_source()
        cls.warehouse_tables = analysis.build_star_schema(cls.tables)
        cls.quality_report, cls.rejected_records = analysis.run_quality_checks(
            cls.tables,
            cls.warehouse_tables,
        )

    def test_no_rejected_records(self):
        self.assertEqual(len(self.rejected_records), 0)

    def test_required_source_tables_are_clean(self):
        for table_name, table_df in self.tables.items():
            if table_name == "rejected_records":
                continue
            self.assertEqual(table_df.isna().sum().sum(), 0, table_name)
            self.assertEqual(table_df.duplicated().sum(), 0, table_name)

    def test_financial_amounts_are_valid(self):
        for table_name, table_df in self.tables.items():
            if table_name == "rejected_records":
                continue
            self.assertTrue((table_df["approved_loans"] >= 0).all(), table_name)
            self.assertTrue((table_df["approved_dollars"] >= 0).all(), table_name)
            self.assertTrue(
                (table_df["approved_sba_guaranty_dollars"] <= table_df["approved_dollars"]).all(),
                table_name,
            )

    def test_star_schema_keys_are_valid(self):
        fact = self.warehouse_tables["fact_lending_activity"]
        dim_lender = self.warehouse_tables["dim_lender"]
        dim_geography = self.warehouse_tables["dim_geography"]

        self.assertFalse(dim_lender["lender_key"].duplicated().any())
        self.assertFalse(dim_geography["geography_key"].duplicated().any())
        self.assertFalse(fact["lender_key"].isna().any())
        self.assertFalse(fact["geography_key"].isna().any())

    def test_all_quality_checks_pass(self):
        failed = self.quality_report[self.quality_report["status"] != "pass"]
        self.assertTrue(failed.empty, failed.to_string(index=False))


if __name__ == "__main__":
    unittest.main()
