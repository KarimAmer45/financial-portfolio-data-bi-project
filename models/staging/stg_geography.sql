-- dbt-inspired staging model: standardize lender-county SBA activity.
-- Source equivalent: data/processed/sba_7a_lender_county_activity_fy2024.csv

CREATE OR REPLACE VIEW staging.stg_geography AS
SELECT
    lender AS lender_name,
    lender_city,
    lender_state,
    project_state AS state,
    project_county AS county,
    CAST(approved_loans AS INTEGER) AS approved_loan_count,
    CAST(approved_dollars AS DECIMAL(18, 2)) AS approved_dollars,
    CAST(approved_sba_guaranty_dollars AS DECIMAL(18, 2)) AS guaranty_dollars,
    CAST(avg_loan_size AS DECIMAL(18, 2)) AS avg_loan_size,
    CAST(guaranty_rate_pct AS DECIMAL(9, 2)) AS guaranty_rate_pct
FROM raw.sba_7a_lender_county_activity_fy2024;
