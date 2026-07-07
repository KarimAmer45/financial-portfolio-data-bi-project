-- State-level rollup of county-grain activity, with exposure share.

with state_totals as (
    select
        project_state,
        count(distinct lender_name) as lender_count,
        sum(approved_loan_count) as approved_loan_count,
        sum(approved_dollars) as approved_dollars,
        sum(guaranty_dollars) as guaranty_dollars
    from {{ ref('stg_lender_county_activity') }}
    group by project_state
)

select
    project_state,
    lender_count,
    approved_loan_count,
    approved_dollars,
    guaranty_dollars,
    approved_dollars / nullif(approved_loan_count, 0) as avg_loan_size,
    guaranty_dollars / nullif(approved_dollars, 0) as guaranty_rate,
    approved_dollars / nullif(sum(approved_dollars) over (), 0) as exposure_share
from state_totals
