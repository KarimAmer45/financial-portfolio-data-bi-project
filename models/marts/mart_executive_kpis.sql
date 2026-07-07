-- dbt-inspired mart model: executive KPI table for BI reporting.

CREATE OR REPLACE TABLE marts.mart_executive_kpis AS
SELECT
    SUM(approved_loan_count) AS total_loan_count,
    SUM(approved_dollars) AS total_approved_dollars,
    SUM(guaranty_dollars) AS total_guaranty_dollars,
    SUM(approved_dollars) / NULLIF(SUM(approved_loan_count), 0) AS average_loan_size,
    SUM(guaranty_dollars) / NULLIF(SUM(approved_dollars), 0) AS guaranty_rate,
    COUNT(DISTINCT lender_key) AS active_lenders,
    COUNT(DISTINCT geography_key) AS active_geographies
FROM marts.fct_lending_activity;
