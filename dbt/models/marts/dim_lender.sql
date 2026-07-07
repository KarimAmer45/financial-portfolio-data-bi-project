-- Lender dimension. Surrogate key ordered by name/city/state for stable output.

with distinct_lenders as (
    select distinct
        lender_name,
        lender_city,
        lender_state
    from {{ ref('stg_lender_activity') }}
)

select
    row_number() over (order by lender_name, lender_city, lender_state) as lender_key,
    lender_name,
    lender_city,
    lender_state
from distinct_lenders
