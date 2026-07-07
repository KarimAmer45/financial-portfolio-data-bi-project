"""Unit tests for the cleaning helpers, using small synthetic frames."""

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sba_bi.cleaning import clean_activity_frame, snake_case  # noqa: E402
from sba_bi.insights import money_short  # noqa: E402

COLUMN_MAP = {
    "Lender": "lender",
    "Lender City": "lender_city",
    "Lender State": "lender_state",
    "Approved Loans": "approved_loans",
    "Approved Dollars": "approved_dollars",
    "Approved SBA Guaranty Dollars": "approved_sba_guaranty_dollars",
}
REQUIRED_TEXT = ["lender", "lender_city", "lender_state"]


def make_raw_frame(rows):
    return pd.DataFrame(rows, columns=list(COLUMN_MAP.keys()))


class SnakeCaseTests(unittest.TestCase):
    def test_basic_conversion(self):
        self.assertEqual(snake_case("Approved SBA Guaranty Dollars"), "approved_sba_guaranty_dollars")

    def test_strips_punctuation_and_whitespace(self):
        self.assertEqual(snake_case("  Lender (City) "), "lender_city")


class MoneyShortTests(unittest.TestCase):
    def test_scales(self):
        self.assertEqual(money_short(31_120_000_000), "$31.1B")
        self.assertEqual(money_short(2_500_000), "$2.5M")
        self.assertEqual(money_short(443_000), "$443K")
        self.assertEqual(money_short(950), "$950")


class CleanActivityFrameTests(unittest.TestCase):
    def test_valid_rows_pass_through_with_derived_columns(self):
        raw = make_raw_frame([
            ["First Bank", "Austin", "TX", 4, 2_000_000, 1_500_000],
            ["Second Bank", "Miami", "FL", 2, 500_000, 375_000],
        ])
        clean, log, rejected = clean_activity_frame(raw, REQUIRED_TEXT, COLUMN_MAP)

        self.assertEqual(len(clean), 2)
        self.assertTrue(rejected.empty)
        self.assertEqual(log["rows_removed"], 0)
        self.assertEqual(clean.loc[0, "avg_loan_size"], 500_000)
        self.assertEqual(clean.loc[0, "guaranty_rate_pct"], 75.0)

    def test_missing_required_value_is_rejected_with_reason(self):
        raw = make_raw_frame([
            ["First Bank", "Austin", "TX", 4, 2_000_000, 1_500_000],
            [None, "Miami", "FL", 2, 500_000, 375_000],
            ["Third Bank", "Reno", "NV", None, 100_000, 80_000],
        ])
        clean, log, rejected = clean_activity_frame(raw, REQUIRED_TEXT, COLUMN_MAP)

        self.assertEqual(len(clean), 1)
        self.assertEqual(len(rejected), 2)
        self.assertEqual(set(rejected["rejection_reason"]), {"missing_required_value"})
        self.assertEqual(log["rows_removed"], 2)

    def test_zero_and_negative_amounts_are_rejected(self):
        raw = make_raw_frame([
            ["First Bank", "Austin", "TX", 4, 2_000_000, 1_500_000],
            ["Zero Bank", "Boise", "ID", 0, 100_000, 80_000],
            ["Negative Bank", "Provo", "UT", 3, -50_000, 0],
        ])
        clean, _log, rejected = clean_activity_frame(raw, REQUIRED_TEXT, COLUMN_MAP)

        self.assertEqual(len(clean), 1)
        self.assertEqual(list(clean["lender"]), ["First Bank"])
        self.assertEqual(set(rejected["rejection_reason"]), {"invalid_amount"})

    def test_fully_blank_rows_are_dropped_without_rejection(self):
        raw = make_raw_frame([
            ["First Bank", "Austin", "TX", 4, 2_000_000, 1_500_000],
            [None, None, None, None, None, None],
        ])
        clean, log, rejected = clean_activity_frame(raw, REQUIRED_TEXT, COLUMN_MAP)

        self.assertEqual(len(clean), 1)
        self.assertTrue(rejected.empty)
        self.assertEqual(log["rows_after_blank_drop"], 1)


if __name__ == "__main__":
    unittest.main()
