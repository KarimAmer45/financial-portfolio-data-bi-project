-- Lender concentration and share metrics.

select
    lender_name,
    lender_city,
    lender_state,
    approved_loan_count,
    approved_dollars,
    guaranty_dollars,
    approved_dollars / nullif(approved_loan_count, 0) as avg_loan_size,
    guaranty_dollars / nullif(approved_dollars, 0) as guaranty_rate,
    approved_dollars / nullif(sum(approved_dollars) over (), 0) as lender_share
from {{ ref('stg_lender_activity') }}
