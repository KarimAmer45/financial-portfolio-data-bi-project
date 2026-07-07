-- Loan counts and dollar amounts must be non-negative.

select *
from {{ ref('fct_lending_activity') }}
where approved_loan_count < 0
   or approved_dollars < 0
   or guaranty_dollars < 0
