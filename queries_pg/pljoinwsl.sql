select
        count(*)
from
        lineitem inner join part on l_partkey = p_partkey
where
        p_partkey <= {selectivity}
