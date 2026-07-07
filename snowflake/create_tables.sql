CREATE OR REPLACE TABLE RAW.SBA_7A_LENDER_ACTIVITY_FY2024 (
    lender STRING,
    lender_city STRING,
    lender_state STRING,
    approved_loans NUMBER(18, 0),
    approved_dollars NUMBER(18, 2),
    approved_sba_guaranty_dollars NUMBER(18, 2),
    avg_loan_size NUMBER(18, 2),
    guaranty_rate_pct NUMBER(9, 2)
);

CREATE OR REPLACE TABLE RAW.SBA_7A_LENDER_COUNTY_ACTIVITY_FY2024 (
    lender STRING,
    lender_city STRING,
    lender_state STRING,
    project_state STRING,
    project_county STRING,
    approved_loans NUMBER(18, 0),
    approved_dollars NUMBER(18, 2),
    approved_sba_guaranty_dollars NUMBER(18, 2),
    avg_loan_size NUMBER(18, 2),
    guaranty_rate_pct NUMBER(9, 2)
);

CREATE OR REPLACE TABLE RAW.SBA_7A_DISTRICT_OFFICE_ACTIVITY_FY2024 (
    lender STRING,
    lender_city STRING,
    lender_state STRING,
    do_code STRING,
    sba_do_name STRING,
    approved_loans NUMBER(18, 0),
    approved_dollars NUMBER(18, 2),
    approved_sba_guaranty_dollars NUMBER(18, 2),
    avg_loan_size NUMBER(18, 2),
    guaranty_rate_pct NUMBER(9, 2)
);

CREATE OR REPLACE TABLE MARTS.DIM_LENDER (
    lender_key NUMBER(18, 0),
    lender_name STRING,
    lender_city STRING,
    lender_state STRING
);

CREATE OR REPLACE TABLE MARTS.DIM_GEOGRAPHY (
    geography_key NUMBER(18, 0),
    state STRING,
    county STRING,
    region STRING
);

CREATE OR REPLACE TABLE MARTS.DIM_DATE (
    date_key NUMBER(18, 0),
    reporting_period DATE,
    year NUMBER(4, 0),
    quarter STRING,
    month NUMBER(2, 0),
    period_label STRING
);

CREATE OR REPLACE TABLE MARTS.FACT_LENDING_ACTIVITY (
    lender_key NUMBER(18, 0),
    geography_key NUMBER(18, 0),
    date_key NUMBER(18, 0),
    reporting_period DATE,
    approved_loan_count NUMBER(18, 0),
    approved_dollars NUMBER(18, 2),
    guaranty_dollars NUMBER(18, 2)
);
