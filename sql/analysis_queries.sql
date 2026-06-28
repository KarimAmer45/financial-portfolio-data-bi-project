-- Analysis queries for the SBA 7(a) lender activity BI project.
-- The Python script loads cleaned workbook sheets into these SQLite tables:
--   sba_lender_activity
--   sba_lender_county_activity
--   sba_district_office_activity

-- name: kpi_summary
WITH totals AS (
    SELECT
        SUM(approved_loans) AS approved_loans,
        SUM(approved_dollars) AS approved_dollars,
        SUM(approved_sba_guaranty_dollars) AS approved_sba_guaranty_dollars
    FROM sba_lender_activity
),
top_10 AS (
    SELECT SUM(approved_dollars) AS top_10_approved_dollars
    FROM (
        SELECT approved_dollars
        FROM sba_lender_activity
        ORDER BY approved_dollars DESC
        LIMIT 10
    )
)
SELECT
    (SELECT COUNT(*) FROM sba_lender_activity) AS lender_count,
    (SELECT COUNT(DISTINCT project_state) FROM sba_lender_county_activity) AS project_state_count,
    (SELECT COUNT(DISTINCT project_state || '|' || project_county) FROM sba_lender_county_activity) AS project_county_count,
    CAST(t.approved_loans AS INTEGER) AS approved_loans,
    ROUND(t.approved_dollars, 2) AS approved_dollars,
    ROUND(t.approved_sba_guaranty_dollars, 2) AS approved_sba_guaranty_dollars,
    ROUND(t.approved_dollars / NULLIF(t.approved_loans, 0), 2) AS avg_loan_size,
    ROUND(100.0 * t.approved_sba_guaranty_dollars / NULLIF(t.approved_dollars, 0), 2) AS guaranty_rate_pct,
    ROUND(100.0 * top_10.top_10_approved_dollars / NULLIF(t.approved_dollars, 0), 2) AS top_10_lender_share_pct
FROM totals t
CROSS JOIN top_10;

-- name: top_lenders
WITH total AS (
    SELECT SUM(approved_dollars) AS approved_dollars
    FROM sba_lender_activity
)
SELECT
    l.lender,
    l.lender_city,
    l.lender_state,
    CAST(l.approved_loans AS INTEGER) AS approved_loans,
    ROUND(l.approved_dollars, 2) AS approved_dollars,
    ROUND(l.approved_sba_guaranty_dollars, 2) AS approved_sba_guaranty_dollars,
    ROUND(l.approved_dollars / NULLIF(l.approved_loans, 0), 2) AS avg_loan_size,
    ROUND(100.0 * l.approved_sba_guaranty_dollars / NULLIF(l.approved_dollars, 0), 2) AS guaranty_rate_pct,
    ROUND(100.0 * l.approved_dollars / NULLIF(total.approved_dollars, 0), 2) AS market_share_pct
FROM sba_lender_activity l
CROSS JOIN total
ORDER BY l.approved_dollars DESC
LIMIT 15;

-- name: project_state_activity
WITH total AS (
    SELECT SUM(approved_dollars) AS approved_dollars
    FROM sba_lender_activity
)
SELECT
    c.project_state,
    COUNT(DISTINCT c.lender) AS lender_count,
    CAST(SUM(c.approved_loans) AS INTEGER) AS approved_loans,
    ROUND(SUM(c.approved_dollars), 2) AS approved_dollars,
    ROUND(SUM(c.approved_sba_guaranty_dollars), 2) AS approved_sba_guaranty_dollars,
    ROUND(SUM(c.approved_dollars) / NULLIF(SUM(c.approved_loans), 0), 2) AS avg_loan_size,
    ROUND(100.0 * SUM(c.approved_sba_guaranty_dollars) / NULLIF(SUM(c.approved_dollars), 0), 2) AS guaranty_rate_pct,
    ROUND(100.0 * SUM(c.approved_dollars) / NULLIF(total.approved_dollars, 0), 2) AS exposure_share_pct
FROM sba_lender_county_activity c
CROSS JOIN total
GROUP BY c.project_state
ORDER BY SUM(c.approved_dollars) DESC;

-- name: county_concentration
WITH total AS (
    SELECT SUM(approved_dollars) AS approved_dollars
    FROM sba_lender_activity
)
SELECT
    c.project_state,
    c.project_county,
    COUNT(DISTINCT c.lender) AS lender_count,
    CAST(SUM(c.approved_loans) AS INTEGER) AS approved_loans,
    ROUND(SUM(c.approved_dollars), 2) AS approved_dollars,
    ROUND(SUM(c.approved_sba_guaranty_dollars), 2) AS approved_sba_guaranty_dollars,
    ROUND(SUM(c.approved_dollars) / NULLIF(SUM(c.approved_loans), 0), 2) AS avg_loan_size,
    ROUND(100.0 * SUM(c.approved_sba_guaranty_dollars) / NULLIF(SUM(c.approved_dollars), 0), 2) AS guaranty_rate_pct,
    ROUND(100.0 * SUM(c.approved_dollars) / NULLIF(total.approved_dollars, 0), 2) AS exposure_share_pct
FROM sba_lender_county_activity c
CROSS JOIN total
GROUP BY c.project_state, c.project_county
ORDER BY SUM(c.approved_dollars) DESC
LIMIT 20;

-- name: lender_geographic_reach
WITH county_reach AS (
    SELECT
        lender,
        lender_city,
        lender_state,
        COUNT(DISTINCT project_state) AS project_states,
        COUNT(DISTINCT project_state || '|' || project_county) AS project_counties,
        SUM(approved_dollars) AS approved_dollars
    FROM sba_lender_county_activity
    GROUP BY lender, lender_city, lender_state
)
SELECT
    l.lender,
    l.lender_city,
    l.lender_state,
    CAST(l.approved_loans AS INTEGER) AS approved_loans,
    ROUND(l.approved_dollars, 2) AS approved_dollars,
    c.project_states,
    c.project_counties,
    ROUND(l.approved_dollars / NULLIF(c.project_states, 0), 2) AS avg_dollars_per_state,
    ROUND(l.approved_dollars / NULLIF(c.project_counties, 0), 2) AS avg_dollars_per_county
FROM sba_lender_activity l
JOIN county_reach c
    ON l.lender = c.lender
    AND l.lender_city = c.lender_city
    AND l.lender_state = c.lender_state
ORDER BY l.approved_dollars DESC
LIMIT 20;

-- name: district_office_activity
SELECT
    do_code,
    sba_do_name,
    COUNT(DISTINCT lender) AS lender_count,
    CAST(SUM(approved_loans) AS INTEGER) AS approved_loans,
    ROUND(SUM(approved_dollars), 2) AS approved_dollars,
    ROUND(SUM(approved_sba_guaranty_dollars), 2) AS approved_sba_guaranty_dollars,
    ROUND(SUM(approved_dollars) / NULLIF(SUM(approved_loans), 0), 2) AS avg_loan_size,
    ROUND(100.0 * SUM(approved_sba_guaranty_dollars) / NULLIF(SUM(approved_dollars), 0), 2) AS guaranty_rate_pct
FROM sba_district_office_activity
GROUP BY do_code, sba_do_name
ORDER BY approved_dollars DESC
LIMIT 20;
