-- dbt-inspired mart model: fact table at lender-county-reporting-period grain.

CREATE OR REPLACE TABLE marts.fct_lending_activity AS
SELECT
    dl.lender_key,
    dg.geography_key,
    20240930 AS date_key,
    '2024-09-30' AS reporting_period,
    g.approved_loan_count,
    g.approved_dollars,
    g.guaranty_dollars
FROM staging.stg_geography g
JOIN marts.dim_lender dl
    ON g.lender_name = dl.lender_name
    AND g.lender_city = dl.lender_city
    AND g.lender_state = dl.lender_state
JOIN marts.dim_geography dg
    ON g.state = dg.state
    AND g.county = dg.county;
