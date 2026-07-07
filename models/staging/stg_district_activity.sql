-- dbt-inspired staging model: standardize SBA district office activity.
-- Source equivalent: data/processed/sba_7a_district_office_activity_fy2024.csv

CREATE OR REPLACE VIEW staging.stg_district_activity AS
SELECT
    lender AS lender_name,
    lender_city,
    lender_state,
    do_code,
    sba_do_name,
    CAST(approved_loans AS INTEGER) AS approved_loan_count,
    CAST(approved_dollars AS DECIMAL(18, 2)) AS approved_dollars,
    CAST(approved_sba_guaranty_dollars AS DECIMAL(18, 2)) AS guaranty_dollars,
    CAST(avg_loan_size AS DECIMAL(18, 2)) AS avg_loan_size,
    CAST(guaranty_rate_pct AS DECIMAL(9, 2)) AS guaranty_rate_pct
FROM raw.sba_7a_district_office_activity_fy2024;
