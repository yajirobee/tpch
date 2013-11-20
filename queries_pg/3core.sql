-- customer table has 150,000 x SF tuples
-- the orders are assigned at random to two-thirds of customers
-- 

select
	count(*)
from
	(customer inner join orders on c_custkey = o_custkey) inner join lineitem on l_orderkey = o_orderkey
where
	c_custkey <= {custkeymax}
