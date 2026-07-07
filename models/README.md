# dbt-Inspired SQL Model Layer

This folder shows how the project would be organized in a dbt-style analytics engineering workflow.

It is intentionally **dbt-inspired standard SQL**, not a fully configured dbt project. The current executable pipeline is `notebooks/analysis.py`, which reads the SBA workbook, exports cleaned CSVs, and builds warehouse-ready fact and dimension tables.

## Layers

- `staging/`: standardized source views that rename and type source fields.
- `intermediate/`: reusable metric and aggregation logic.
- `marts/`: reporting-ready fact, dimension, and KPI tables.

## Suggested Tests

- `lender_key` and `geography_key` are non-null in facts.
- Dimension keys are unique.
- Approved dollars and approved loan counts are non-negative.
- SBA guaranty dollars do not exceed approved dollars.
- State codes are valid U.S. states or territories.
- Fact rows match lender and geography dimensions.
