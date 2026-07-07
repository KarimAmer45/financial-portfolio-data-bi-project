-- SBA guaranty dollars should never exceed approved dollars on a fact row.

select *
from {{ ref('fct_lending_activity') }}
where guaranty_dollars > approved_dollars
