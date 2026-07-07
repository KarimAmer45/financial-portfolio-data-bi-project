-- Lender by project-county activity. This is the grain of the fact table.

select
    lender as lender_name,
    lender_city,
    lender_state,
    project_state,
    project_county,
    cast(approved_loans as integer) as approved_loan_count,
    cast(approved_dollars as decimal(18, 2)) as approved_dollars,
    cast(approved_sba_guaranty_dollars as decimal(18, 2)) as guaranty_dollars
from {{ source('sba_raw', 'sba_7a_lender_county_activity_fy2024') }}
