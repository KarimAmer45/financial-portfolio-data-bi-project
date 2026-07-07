# Snowflake Migration Layer

Snowflake-compatible SQL and loading notes for moving this workflow into a
warehouse. To be clear about scope: this SQL is written and organized for
Snowflake but has not been executed against a live Snowflake account. The
dbt project in `dbt/` runs the same transformations locally on DuckDB.

## Schemas

- `RAW` - source extracts loaded via `COPY INTO`.
- `STAGING` - typed and renamed source views.
- `MARTS` - fact, dimension, and KPI reporting tables.

## Execution order

1. `create_schemas.sql`
2. Create a file format and internal stage, then `PUT` the CSVs from
   `data/processed/` (see comments in `copy_into_examples.sql`).
3. `create_tables.sql`
4. `copy_into_examples.sql`
5. Point the dbt project's profile at Snowflake and run `dbt build` so the
   staging/marts models materialize in the warehouse instead of DuckDB.

## What would run where

Cleaning and rejection of malformed source rows stays in Python at ingest.
Everything after that - typing, renaming, dimension keys, fact assembly,
KPI rollups - is set-based SQL and belongs in the warehouse, which is why
the dbt models mirror `src/sba_bi/warehouse.py`.
