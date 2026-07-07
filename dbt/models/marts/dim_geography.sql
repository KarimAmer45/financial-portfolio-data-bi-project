-- Geography dimension at project state/county grain, with census region
-- from the state_regions seed.

with distinct_geographies as (
    select distinct
        project_state as state,
        project_county as county
    from {{ ref('stg_lender_county_activity') }}
)

select
    row_number() over (order by g.state, g.county) as geography_key,
    g.state,
    g.county,
    coalesce(r.region, 'Unknown') as region
from distinct_geographies g
left join {{ ref('state_regions') }} r
    on g.state = r.state
