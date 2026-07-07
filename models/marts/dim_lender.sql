-- dbt-inspired mart model: lender dimension.

CREATE OR REPLACE TABLE marts.dim_lender AS
SELECT
    ROW_NUMBER() OVER (ORDER BY lender_name, lender_city, lender_state) AS lender_key,
    lender_name,
    lender_city,
    lender_state
FROM (
    SELECT DISTINCT
        lender_name,
        lender_city,
        lender_state
    FROM staging.stg_lender_activity
);
