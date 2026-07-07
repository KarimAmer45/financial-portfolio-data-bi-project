-- Lender by SBA district office activity. Kept separate from the county-grain
-- fact because the two aggregations do not join cleanly at the same grain.

select
    lender as lender_name,
    lender_city,
    lender_state,
    do_code,
    sba_do_name as district_office_name,
    cast(approved_loans as integer) as approved_loan_count,
    cast(approved_dollars as decimal(18, 2)) as approved_dollars,
    cast(approved_sba_guaranty_dollars as decimal(18, 2)) as guaranty_dollars
from {{ source('sba_raw', 'sba_7a_district_office_activity_fy2024') }}
