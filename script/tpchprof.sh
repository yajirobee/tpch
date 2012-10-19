#! /bin/bash

for i in {1..10}
do
iostat -x 1 | awk '$1 ~ /^(md0|fio[a-h])$/ { print $0 } NF == 0 { print "" }' > /data/local/keisuke/tpch/q${i}.io &
mpstat -P ALL 1 | awk '$3 >= 3.0 && $2 ~ /^[0-9]+$/ { print $0 }' > /data/local/keisuke/tpch/q${i}.cpu &
(time psql -d tpch -f ${i}.ana) > /data/local/keisuke/tpch/q${i}analyze.res 2>&1
pkill -f iostat -U keisuke
pkill -f mpstat -U keisuke
done
