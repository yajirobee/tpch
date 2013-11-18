#! /bin/bash

user=`whoami`
date=`date '+%Y%m%d%H%M%S'`

queryfile=${1}
basename=`basename ${1}`
basename_woext=${1%.*}
datadir=/data/local/keisuke/tpch/${date}
devlist="/dev/md0 /dev/fio[abcdefgh]"

ioproffile=${datadir}/${basename_woext}.io
cpuproffile=${datadir}/${basename_woext}.cpu
resultfile=${datadir}/${basename_woext}.res
topfile=${datadir}/${basename_woext}.top

mkdir -p ${datadir}
echo "execute query : ${1}"
#blktrace ${devlist} -D ${datadir} &
sleep 1
iostat -x 1 > ${ioproffile} &
mpstat -P ALL 1 > ${cpuproffile} &
#top -b -d 5 > ${topfile} &
(time psql -d tpch -U keisuke -f ${queryfile}) > ${resultfile} 2>&1
#pkill -f top -U ${user}
pkill -f iostat -U ${user}
pkill -f mpstat -U ${user}
#pkill -f blktrace -U ${user}
