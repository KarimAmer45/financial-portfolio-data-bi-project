# Power BI Report

This folder contains a Power BI project (`sba_lending.pbip`) with the semantic
model already built: all four star-schema tables, the two data-quality tables,
relationships, and the DAX measures.

## Opening the project

1. Open `powerbi/sba_lending.pbip` in Power BI Desktop.
2. If the data folder is not found, update the `DataRoot` parameter
   (Transform data > Manage parameters) to the absolute path of this
   repository's `data/` folder, then refresh.
3. Lay out the visuals on the four report pages following
   [dashboard_pages.md](dashboard_pages.md).

The semantic model loads from the CSVs in `data/warehouse/` and
`data/quality/`, so run the pipeline first if those are missing:

```bash
python src/run_pipeline.py
```

## Model

| Table | Role |
| --- | --- |
| fact_lending_activity | Activity at lender x county x period grain |
| dim_lender | Lender attributes |
| dim_geography | Project state, county, census region |
| dim_date | Reporting period |
| data_quality_report | One row per pipeline quality check |
| rejected_records | Rows rejected during cleaning |

Relationships are many-to-one from the fact table to each dimension with
single-direction filters. The data-quality tables are intentionally
disconnected; they feed the Data Quality page directly.

Measures live on `fact_lending_activity` and are documented in
[dax_measures.md](dax_measures.md).

## Refresh flow

Replace the raw workbook under `data/raw/`, run the pipeline, then refresh
the model in Power BI Desktop. Page layout and measures are unaffected by a
data refresh.
