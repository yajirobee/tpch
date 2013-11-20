-- customer table has 150,000 x SF tuples
-- the orders are assigned at random to two-thirds of customers
-- 
explain
select
	count(*)
from
	customer,
	orders,
	lineitem
where
	c_custkey = o_custkey
	and l_orderkey = o_orderkey
	and c_custkey <= 1000
