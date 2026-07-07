-- Fact table at lender x project county x reporting period grain.
-- The source is aggregated SBA activity, so there is no loan-level detail
-- below this grain.

select
    dl.lender_key,
    dg.geography_key,
    dd.date_key,
    dd.reporting_period,
    c.approved_loan_count,
    c.approved_dollars,
    c.guaranty_dollars
from {{ ref('stg_lender_county_activity') }} c
join {{ ref('dim_lender') }} dl
    on c.lender_name = dl.lender_name
    and c.lender_city = dl.lender_city
    and c.lender_state = dl.lender_state
join {{ ref('dim_geography') }} dg
    on c.project_state = dg.state
    and c.project_county = dg.county
cross join {{ ref('dim_date') }} dd
