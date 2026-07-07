# Snowflake-Ready Layer

This folder contains Snowflake-compatible SQL and loading notes for moving the local SBA BI workflow into a warehouse.

This project has not been executed against Snowflake in this repository. The SQL is a migration-ready design that shows how the same workflow would be organized in Snowflake schemas.

## Proposed Schemas

- `RAW`: externally loaded source extracts.
- `STAGING`: typed and renamed source views.
- `MARTS`: fact, dimension, and KPI reporting tables.

## Execution Order

1. Run `create_schemas.sql`.
2. Create a file format and internal stage.
3. Upload processed CSVs from `data/processed/` and `data/warehouse/`.
4. Run `create_tables.sql`.
5. Adapt and run `copy_into_examples.sql`.
6. Run dbt-inspired SQL from `models/` or translate it into actual dbt models.

## Interview Framing

I designed a Snowflake-ready architecture and wrote the relevant schema and loading SQL. I did not claim this repository is a verified production Snowflake deployment.
