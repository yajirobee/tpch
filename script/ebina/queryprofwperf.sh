#! /bin/bash

user=`whoami`
date=`date '+%Y%m%d%H%M%S'`

queryfile=${1}
basename=`basename ${1}`
basename_woext=${1%.*}
datadir=/data/local/keisuke/tpch/${date}

ioproffile=${datadir}/${basename_woext}.io
cpuproffile=${datadir}/${basename_woext}.cpu
resultfile=${datadir}/${basename_woext}.res
topfile=${datadir}/${basename_woext}.top
perffile=${datadir}/${basename_woext}.perf

cmd=

mkdir -p ${datadir}
echo "execute query : ${1}"
iostat -x 1 > ${ioproffile} &
mpstat -P ALL 1 > ${cpuproffile} &
#top -b -d 5 > ${topfile} &
#perf record -a -g -e cache-misses -o ${perffile} -f -- time -a -o ${resultfile} psql -d tpch -U keisuke -f ${queryfile} > ${resultfile}
perf stat -a -e cycles,cache-references,cache-misses,faults,minor-faults,major-faults -o ${perffile} -- time -a -o ${resultfile} psql -d tpch -U keisuke -f ${queryfile} > ${resultfile}
#pkill -f top -U ${user}
pkill -f iostat -U ${user}
pkill -f mpstat -U ${user}
