#! /bin/bash

queryfile=${1}
basename=`basename ${1}`
basename_woext=${basename%.*}
explainfile=${2}
datadir=/data/local/keisuke/tpch

echo "execute query : ${1}"
for i in {1..5}
do
ioproffile=${datadir}/${basename_woext}_${i}.io
cpuproffile=${datadir}/${basename_woext}_${i}.cpu
resultfile=${datadir}/${basename_woext}_${i}.res
planfile=${datadir}/${basename_woext}_${i}.exp

psql -d tpch -f ${explainfile} > ${planfile}
clearcache
pg start
sleep 5
iostat -x 1 > ${ioproffile} &
mpstat -P ALL 1 > ${cpuproffile} &
(time psql -d tpch -f ${queryfile}) > ${resultfile} 2>&1
pkill -f iostat -U keisuke
pkill -f mpstat -U keisuke
pg stop
done
