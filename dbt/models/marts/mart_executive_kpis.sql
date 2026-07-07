-- Executive KPI rollup used by the overview report page.

select
    sum(approved_loan_count) as total_loan_count,
    sum(approved_dollars) as total_approved_dollars,
    sum(guaranty_dollars) as total_guaranty_dollars,
    sum(approved_dollars) / nullif(sum(approved_loan_count), 0) as average_loan_size,
    sum(guaranty_dollars) / nullif(sum(approved_dollars), 0) as guaranty_rate,
    count(distinct lender_key) as active_lenders,
    count(distinct geography_key) as active_geographies
from {{ ref('fct_lending_activity') }}
