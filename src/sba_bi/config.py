"""Project paths, constants, and source sheet configuration."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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

NUMERIC_COLUMNS = ["approved_loans", "approved_dollars", "approved_sba_guaranty_dollars"]

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


def load_sheet_config(path: Path = CONFIG_PATH) -> dict[str, dict]:
    """Read the workbook sheet/column mapping from config/column_mappings.json."""
    if not path.exists():
        raise FileNotFoundError(
            f"Column mapping config not found: {path}. "
            "The pipeline needs it to know which sheets and columns to load."
        )
    config = json.loads(path.read_text(encoding="utf-8"))
    return config["tables"]
