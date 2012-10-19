#! /bin/bash

queryfile=${1}
basename_woext=${1%.*}
ioproffile=/data/local/keisuke/tpch/disk/${basename_woext}.io
cpuproffile=/data/local/keisuke/tpch/disk/${basename_woext}.cpu
resultfile=/data/local/keisuke/tpch/disk/${basename_woext}.res

echo "execute query : ${1}"
iostat -x 1 | awk '$1 ~ /^(md0|fio[a-h])$/ { print $0 } NF == 0 { print "" }' > ${ioproffile} &
mpstat -P ALL 1 | awk '$4 >= 3.0 && $2 ~ /^[0-9]+$/ { print $0 }' > ${cpuproffile} &
(time psql -d tpchdisk -f ${queryfile}) > ${resultfile} 2>&1
pkill -f iostat -U keisuke
pkill -f mpstat -U keisuke
