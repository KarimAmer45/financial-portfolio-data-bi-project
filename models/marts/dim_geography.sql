-- dbt-inspired mart model: geography dimension.

CREATE OR REPLACE TABLE marts.dim_geography AS
SELECT
    ROW_NUMBER() OVER (ORDER BY state, county) AS geography_key,
    state,
    county,
    'Not provided at county grain' AS district,
    CASE
        WHEN state IN ('CT', 'ME', 'MA', 'NH', 'RI', 'VT', 'NJ', 'NY', 'PA') THEN 'Northeast'
        WHEN state IN ('IL', 'IN', 'MI', 'OH', 'WI', 'IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD') THEN 'Midwest'
        WHEN state IN ('DE', 'DC', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'WV', 'AL', 'KY', 'MS', 'TN', 'AR', 'LA', 'OK', 'TX') THEN 'South'
        WHEN state IN ('AK', 'AZ', 'CA', 'CO', 'HI', 'ID', 'MT', 'NV', 'NM', 'OR', 'UT', 'WA', 'WY') THEN 'West'
        WHEN state IN ('PR', 'GU', 'VI', 'AS', 'MP') THEN 'Territory'
        ELSE 'Unknown'
    END AS region
FROM (
    SELECT DISTINCT
        state,
        county
    FROM staging.stg_geography
);
