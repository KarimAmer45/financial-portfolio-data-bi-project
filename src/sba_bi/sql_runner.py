"""Run the named SQL analysis queries against the cleaned tables in SQLite."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd

from . import config

logger = logging.getLogger(__name__)


def load_named_queries(path: Path = config.SQL_PATH) -> dict[str, str]:
    """Parse `-- name: <query_name>` sections out of the analysis SQL file."""
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
    queries = load_named_queries()
    logger.info("Running %s SQL analysis queries", len(queries))
    with sqlite3.connect(":memory:") as connection:
        for table_name, table_df in tables.items():
            table_df.to_sql(table_name, connection, if_exists="replace", index=False)
        return {name: pd.read_sql_query(query, connection) for name, query in queries.items()}
