# Report Page Layout

The PBIP project ships with four empty, named pages. This is the layout each
page is meant to carry.

## 1. Executive Overview

The at-a-glance view of FY2024 7(a) activity.

- KPI cards across the top: Total Approved Dollars, Total Loan Count,
  Average Loan Size, Total Guaranty Dollars, Guaranty Rate, Active Lenders.
- Bar chart: top 10 lenders by Total Approved Dollars (`dim_lender[lender_name]`).
- Bar chart or filled map: approved dollars by `dim_geography[state]`. Prefer
  the bar chart if map geocoding of two-letter codes is unreliable.
- Card: Top 10 Lender Share, as the concentration headline.

## 2. Lender Analysis

Compare lenders on scale and concentration.

- Slicer: `dim_lender[lender_name]`.
- Bar chart: Total Approved Dollars by lender.
- Bar chart: Total Loan Count by lender.
- Scatter: Average Loan Size vs Total Approved Dollars, one point per lender.
- Table: lender, Total Approved Dollars, Total Loan Count, Average Loan Size,
  Guaranty Rate, Lender Share.

## 3. Geographic Analysis

Where the dollars land.

- Slicer: `dim_geography[state]`.
- Bar charts: Total Approved Dollars and Total Loan Count by state.
- Matrix or bar chart: rollup by `dim_geography[region]`.
- Table: state, county, Total Approved Dollars, Total Loan Count,
  Average Loan Size.

## 4. Data Quality

Operational trust page for the model itself.

- KPI cards: count of fact rows, Failed Data Quality Checks,
  Rejected Record Count, and `dim_date[reporting_period]` as refresh context.
- Table: `data_quality_report` with check name, status, failed count, details.
- Table: `rejected_records`.

## Refresh

```bash
python src/run_pipeline.py
```

Then Refresh in Power BI Desktop. The pages and measures stay put; only the
data changes.
