# Power BI Dashboard Design

This folder documents the Power BI report design for the generated star-schema tables in `data/warehouse/`.

Power BI Desktop is not available in this environment, so no `.pbix` file is committed. The repository provides the model tables, relationship design, DAX measures, and page blueprint needed to build the report quickly and explain it in an interview.

## Tables to Load

- `data/warehouse/fact_lending_activity.csv`
- `data/warehouse/dim_lender.csv`
- `data/warehouse/dim_geography.csv`
- `data/warehouse/dim_date.csv`
- `data/quality/data_quality_report.csv`
- `data/quality/rejected_records.csv`

## Relationships

- `FactLendingActivity[lender_key]` many-to-one `DimLender[lender_key]`
- `FactLendingActivity[geography_key]` many-to-one `DimGeography[geography_key]`
- `FactLendingActivity[date_key]` many-to-one `DimDate[date_key]`

Use single-direction filters from dimensions to fact.

## Report Pages

1. Executive Overview
2. Lender Analysis
3. Geographic Analysis
4. Data Quality

See `dashboard_pages.md` for visual layout and `dax_measures.md` for measures.
