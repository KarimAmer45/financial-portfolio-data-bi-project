# Dashboard Page Blueprint

## 1. Executive Overview

Purpose: show the overall SBA 7(a) FY2024 lending activity at a glance.

Recommended visuals:

- KPI cards: Total Approved Dollars, Total Loan Count, Average Loan Size, Total Guaranty Dollars, Guaranty Rate, Active Lenders.
- Bar chart: Top 10 lenders by approved dollars.
- Filled map or bar chart: Approved dollars by state. Use a bar chart if map geocoding is unreliable.
- Concentration card: Top 10 Lender Share.

## 2. Lender Analysis

Purpose: compare lenders by activity, scale, and concentration.

Recommended visuals:

- Lender slicer.
- Bar chart: approved dollars by lender.
- Bar chart: loan count by lender.
- Scatter plot: average loan size vs. approved dollars.
- Table: lender name, approved dollars, loan count, average loan size, guaranty rate, lender share.

## 3. Geographic Analysis

Purpose: show where approved dollars and loan counts are concentrated.

Recommended visuals:

- State slicer.
- Bar chart: approved dollars by state.
- Bar chart: loan count by state.
- Table: state, county, approved dollars, loan count, average loan size.
- Region summary using `DimGeography[region]`.

## 4. Data Quality

Purpose: demonstrate operational BI thinking beyond visual design.

Recommended visuals:

- KPI cards: processed fact rows, failed data-quality checks, rejected record count, refresh date.
- Table: data-quality checks with status, failed count, and details.
- Table: rejected records.
- Card: source workbook name and reporting period.

## Refresh Notes

After replacing the SBA workbook, run:

```bash
python notebooks/analysis.py
```

Then refresh the Power BI model from the regenerated CSV files.
