-- The county-grain fact should reconcile to lender-level source totals.
-- Fails if approved dollars drift by more than one cent per comparison.

with fact_total as (
    select sum(approved_dollars) as approved_dollars
    from {{ ref('fct_lending_activity') }}
),

source_total as (
    select sum(approved_dollars) as approved_dollars
    from {{ ref('stg_lender_county_activity') }}
)

select *
from fact_total, source_total
where abs(fact_total.approved_dollars - source_total.approved_dollars) > 0.01
