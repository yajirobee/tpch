#! /bin/bash

for i in {1..10}
do
echo "query ${i} launched"
iostat -x 1 | awk '$1 ~ /^(sda|dm-[01])$/ { print $0 } NF == 0 { print "" }' >> /data/local/keisuke/tpch/disk/q${i}.io &
mpstat -P ALL 1 | awk '$3 >= 3.0 && $2 ~ /^[0-9]+$/ { print $0 }' >> /data/local/keisuke/tpch/disk/q${i}.cpu &
(time psql -d tpchdisk -f ${i}.ana) > q${i}analyze.res 2>&1
pkill -f iostat -U keisuke
pkill -f mpstat -U keisuke
done
