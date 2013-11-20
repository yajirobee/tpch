#! /bin/bash

user=`whoami`
queryfile=${1}
basename=`basename ${1}`
basename_woext=${1%.*}
datadir=/data/local/keisuke/tpch
ioproffile=${datadir}/${basename_woext}.io
cpuproffile=${datadir}/${basename_woext}.cpu
resultfile=${datadir}/${basename_woext}.res
perffile=${datadir}/${basename_woext}.perf

echo "execute query : ${1}"
iostat -x 1 > ${ioproffile} &
mpstat -P ALL 1 > ${cpuproffile} &
#top -b -d 5 > ${datadir}/${basename_woext}.top &
perf record -a -o ${perffile} -- sleep 20 &
(time psql -d tpch -U keisuke -f ${queryfile}) > ${resultfile} 2>&1
#time -a -o ${resultfile} psql -d tpch -U keisuke -f ${queryfile} > ${resultfile}
#pkill -f top -U keisuke
pkill -f iostat -U ${user}
pkill -f mpstat -U ${user}
