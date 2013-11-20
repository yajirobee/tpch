select
	extract(year from o_orderdate) as o_year,
	l_extendedprice * (1 - l_discount) as volume,
	n2.n_name as nation
from
	(((lineitem inner join
    (orders inner join
    (customer inner join
    (nation n1 inner join region on n1.n_regionkey = r_regionkey)
    on c_nationkey = n1.n_nationkey)
    on o_custkey = c_custkey)
    on l_orderkey = o_orderkey)
    inner join part on p_partkey = l_partkey)
    inner join supplier on s_suppkey = l_suppkey)
    inner join nation n2 on s_nationkey = n2.n_nationkey
where
	r_name = 'AMERICA'
	and o_orderdate between date '1995-01-01' and date '1996-12-31'
	and p_type = 'ECONOMY ANODIZED STEEL'
