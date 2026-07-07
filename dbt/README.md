# dbt Project

Small dbt project that rebuilds the reporting layer on DuckDB. It reads the
cleaned CSVs produced by the Python pipeline, so run that first if the files
under `data/processed/` are missing.

## Setup and Run

```bash
pip install dbt-duckdb

# from the repository root
dbt build --project-dir dbt --profiles-dir dbt
```

`dbt build` runs the seed, all models, and all tests. The DuckDB database is
written to `dbt/target/sba.duckdb` (not committed).

## Layers

- `staging/` - views that rename and type the raw CSV columns, nothing else.
- `intermediate/` - lender share and state-level metrics.
- `marts/` - the star schema (`fct_lending_activity`, `dim_lender`,
  `dim_geography`, `dim_date`) plus `mart_executive_kpis`.

The `state_regions` seed maps state codes to census regions for
`dim_geography`.

## Tests

Schema tests cover unique and non-null dimension keys, non-null fact foreign
keys, relationships from the fact to each dimension, and accepted region
values. Singular tests check that guaranty dollars never exceed approved
dollars, that no amounts are negative, and that fact totals reconcile to the
staging layer.

## Notes

The same transformations also exist procedurally in `src/sba_bi/warehouse.py`,
which is what feeds Power BI today. This project is the warehouse-native
version of that logic: swap the DuckDB profile for a Snowflake profile and
point the sources at `RAW` tables (see `snowflake/`) and the models carry over
mostly unchanged.
