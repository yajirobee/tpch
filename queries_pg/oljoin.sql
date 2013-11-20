select
        count(*)
from
        lineitem inner join orders on o_orderkey = l_orderkey
