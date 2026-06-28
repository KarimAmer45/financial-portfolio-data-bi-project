# SBA 7(a) Lender Activity Data & BI Project

This project demonstrates a compact Business Intelligence workflow using official U.S. Small Business Administration open data. It cleans an SBA 7(a) lender activity workbook, exports analysis-ready CSV files, runs SQL queries, calculates KPIs, and creates a short business readout with visuals.

The dataset is public, aggregated SBA lending activity data for FY2024. It is not borrower-level credit performance data, so the analysis focuses on lender concentration, geographic exposure, approved loan volume, approved dollars, average loan size, and SBA guaranty exposure.

## Data Source

- Source: U.S. Small Business Administration Open Data
- Dataset: SBA 7(a) & 504 Activity Reports, FY2024 Year End
- Raw file used: `lender7aactivity_fy2024_20240930.xlsx`
- Source URL: https://web.data.sba.gov/en/dataset/7-a-504-activity-reports-fy2024-year-end

## Tools Used

- Python
- pandas and numpy
- openpyxl
- SQLite SQL
- Pillow for PNG chart generation

## Workflow

1. Load the raw SBA workbook from `data/raw/`.
2. Clean and standardize lender, county, and district office sheets.
3. Export cleaned CSV files to `data/processed/`.
4. Load the cleaned tables into SQLite.
5. Run SQL queries for KPIs, lender concentration, geographic exposure, and district office activity.
6. Create BI-style visuals and summarize business insights.

## Data Cleaning Summary

| Table | Raw rows | Clean rows | Notes |
| --- | ---: | ---: | --- |
| Lender activity | 1,472 | 1,472 | Standardized fields and numeric types |
| Lender-county activity | 20,846 | 20,846 | Standardized lender, state, county, and dollar fields |
| District office activity | 6,106 | 6,106 | Standardized district office fields |

The selected SBA sheets had no missing values or duplicate rows after cleaning.

## Key Business Questions

- Which lenders account for the largest approved SBA 7(a) dollar volume?
- How concentrated is activity among the top lenders?
- Which project states and counties drive the most approved dollars?
- Which SBA district offices show the highest activity?
- What is the overall SBA guaranty rate?
- What is the average approved loan size?

## KPI Summary

| KPI | Value |
| --- | ---: |
| Approved loans | 70,242 |
| Approved dollars | $31.12B |
| SBA guaranty dollars | $22.75B |
| Active lenders | 1,472 |
| Project states/territories | 54 |
| Project counties | 2,402 |
| Average loan size | $443K |
| SBA guaranty rate | 73.08% |
| Top 10 lender share | 33.15% |

## Key Insights

- SBA 7(a) FY2024 activity totals $31.1B across 70,242 approved loans and 1,472 lenders.
- SBA guaranty exposure totals $22.7B, equal to 73.08% of approved dollars.
- The top 10 lenders account for 33.15% of approved dollars, showing meaningful but not extreme lender concentration.
- Newtek Bank, National Association is the largest lender by approved dollars at $2.1B, representing 6.74% of total activity.
- California is the largest project state at $4.0B, representing 12.93% of approved dollars.
- Los Angeles County, CA is the largest county exposure at $1.2B.
- South Florida District Office is the largest SBA district office view at $2.0B.

## Visuals

![KPI summary](visuals/kpi_summary.png)

![Top lenders](visuals/top_lenders.png)

![Top project states](visuals/top_project_states.png)

![Top district offices](visuals/top_district_offices.png)

## Repository Structure

```text
financial-portfolio-data-bi-project/
|-- data/
|   |-- raw/
|   |   `-- lender7aactivity_fy2024_20240930.xlsx
|   `-- processed/
|       |-- sba_7a_lender_activity_fy2024.csv
|       |-- sba_7a_lender_county_activity_fy2024.csv
|       `-- sba_7a_district_office_activity_fy2024.csv
|-- sql/
|   `-- analysis_queries.sql
|-- notebooks/
|   `-- analysis.py
|-- visuals/
|   |-- kpi_summary.png
|   |-- top_lenders.png
|   |-- top_project_states.png
|   `-- top_district_offices.png
|-- requirements.txt
`-- README.md
```

## How to Run

```bash
pip install -r requirements.txt
python notebooks/analysis.py
```

Running the script regenerates the cleaned CSV exports, executes the SQL analysis, prints the KPI summary and insights, and refreshes the visuals.

## Relevance to Data & BI

This project reflects Data and Business Intelligence skills including public data sourcing, spreadsheet ingestion, data cleaning, SQL querying, KPI development, exposure analysis, visualization, and clear business communication.
