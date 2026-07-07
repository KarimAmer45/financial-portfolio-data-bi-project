-- dbt-inspired intermediate model: state and county exposure metrics.

CREATE OR REPLACE VIEW intermediate.int_geographic_metrics AS
WITH totals AS (
    SELECT SUM(approved_dollars) AS total_approved_dollars
    FROM staging.stg_lender_activity
)
SELECT
    g.state,
    g.county,
    COUNT(DISTINCT g.lender_name) AS lender_count,
    SUM(g.approved_loan_count) AS approved_loan_count,
    SUM(g.approved_dollars) AS approved_dollars,
    SUM(g.guaranty_dollars) AS guaranty_dollars,
    SUM(g.approved_dollars) / NULLIF(SUM(g.approved_loan_count), 0) AS avg_loan_size,
    SUM(g.guaranty_dollars) / NULLIF(SUM(g.approved_dollars), 0) AS guaranty_rate,
    SUM(g.approved_dollars) / NULLIF(t.total_approved_dollars, 0) AS exposure_share
FROM staging.stg_geography g
CROSS JOIN totals t
GROUP BY g.state, g.county, t.total_approved_dollars;
