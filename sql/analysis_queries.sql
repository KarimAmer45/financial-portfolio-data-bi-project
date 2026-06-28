-- Analysis queries for the loan/customer portfolio mini-project.
-- The Python script loads the cleaned dataset into a SQLite table named loan_portfolio.

-- name: kpi_summary
SELECT
    COUNT(*) AS loans,
    COUNT(DISTINCT customer_id) AS customers,
    ROUND(SUM(outstanding_balance), 2) AS total_outstanding,
    ROUND(AVG(interest_rate) * 100, 2) AS avg_interest_rate_pct,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 30 THEN 1 ELSE 0 END), 2) AS delinquency_rate_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct,
    ROUND(SUM(outstanding_balance * ltv) / NULLIF(SUM(outstanding_balance), 0), 3) AS weighted_avg_ltv,
    ROUND(
        100.0 * SUM(CASE WHEN risk_bucket IN ('Elevated', 'High') THEN outstanding_balance ELSE 0 END)
        / NULLIF(SUM(outstanding_balance), 0),
        2
    ) AS exposure_at_risk_pct
FROM loan_portfolio;

-- name: monthly_trend
SELECT
    substr(origination_date, 1, 7) AS month,
    COUNT(*) AS new_loans,
    ROUND(SUM(loan_amount), 2) AS originated_amount,
    ROUND(AVG(interest_rate) * 100, 2) AS avg_interest_rate_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct
FROM loan_portfolio
GROUP BY substr(origination_date, 1, 7)
ORDER BY month;

-- name: region_performance
SELECT
    region,
    COUNT(*) AS loans,
    ROUND(SUM(outstanding_balance), 2) AS total_outstanding,
    ROUND(AVG(interest_rate) * 100, 2) AS avg_interest_rate_pct,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 30 THEN 1 ELSE 0 END), 2) AS delinquency_rate_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct,
    ROUND(AVG(ltv), 3) AS avg_ltv,
    ROUND(AVG(debt_service_coverage_ratio), 2) AS avg_dscr
FROM loan_portfolio
GROUP BY region
ORDER BY total_outstanding DESC;

-- name: segment_performance
SELECT
    customer_segment,
    COUNT(*) AS loans,
    ROUND(SUM(outstanding_balance), 2) AS total_outstanding,
    ROUND(AVG(credit_score), 0) AS avg_credit_score,
    ROUND(AVG(interest_rate) * 100, 2) AS avg_interest_rate_pct,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 30 THEN 1 ELSE 0 END), 2) AS delinquency_rate_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct,
    ROUND(AVG(ltv), 3) AS avg_ltv
FROM loan_portfolio
GROUP BY customer_segment
ORDER BY total_outstanding DESC;

-- name: product_performance
SELECT
    loan_product,
    COUNT(*) AS loans,
    ROUND(SUM(outstanding_balance), 2) AS total_outstanding,
    ROUND(AVG(interest_rate) * 100, 2) AS avg_interest_rate_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct,
    ROUND(AVG(ltv), 3) AS avg_ltv
FROM loan_portfolio
GROUP BY loan_product
ORDER BY total_outstanding DESC;

-- name: risk_bucket_summary
SELECT
    risk_bucket,
    COUNT(*) AS loans,
    ROUND(SUM(outstanding_balance), 2) AS total_outstanding,
    ROUND(100.0 * SUM(outstanding_balance) / SUM(SUM(outstanding_balance)) OVER (), 2) AS exposure_share_pct,
    ROUND(AVG(interest_rate) * 100, 2) AS avg_interest_rate_pct,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 30 THEN 1 ELSE 0 END), 2) AS delinquency_rate_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct
FROM loan_portfolio
GROUP BY risk_bucket
ORDER BY
    CASE risk_bucket
        WHEN 'Low' THEN 1
        WHEN 'Moderate' THEN 2
        WHEN 'Elevated' THEN 3
        WHEN 'High' THEN 4
        ELSE 5
    END;

-- name: industry_concentration
SELECT
    industry,
    COUNT(*) AS loans,
    ROUND(SUM(outstanding_balance), 2) AS total_outstanding,
    ROUND(100.0 * SUM(outstanding_balance) / SUM(SUM(outstanding_balance)) OVER (), 2) AS exposure_share_pct,
    ROUND(100.0 * AVG(default_flag), 2) AS default_rate_pct,
    ROUND(100.0 * AVG(CASE WHEN days_past_due >= 30 THEN 1 ELSE 0 END), 2) AS delinquency_rate_pct
FROM loan_portfolio
GROUP BY industry
ORDER BY total_outstanding DESC
LIMIT 8;
