-- using default substitutions


explain
select
	l_returnflag,
	l_linestatus,
	count(*) as count_order
from
	lineitem
where
	l_shipdate <= date '1992-02-28'
group by
	l_returnflag,
	l_linestatus
order by
	l_returnflag,
	l_linestatus;
