-- dbt-inspired intermediate model: lender concentration and share metrics.

CREATE OR REPLACE VIEW intermediate.int_lender_metrics AS
WITH totals AS (
    SELECT SUM(approved_dollars) AS total_approved_dollars
    FROM staging.stg_lender_activity
)
SELECT
    l.lender_name,
    l.lender_city,
    l.lender_state,
    l.approved_loan_count,
    l.approved_dollars,
    l.guaranty_dollars,
    l.avg_loan_size,
    l.guaranty_rate_pct,
    l.approved_dollars / NULLIF(t.total_approved_dollars, 0) AS lender_share
FROM staging.stg_lender_activity l
CROSS JOIN totals t;
