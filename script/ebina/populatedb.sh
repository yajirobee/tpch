#! /bin/bash -x

pgbindir=/data/local/keisuke/local/bin
dbname=${1}

${pgbindir}/createdb --username=keisuke --tablespace=iod8raid0 ${dbname}
${pgbindir}/psql --username=keisuke --dbname=${dbname} --file=createtable.sql
${pgbindir}/psql --username=keisuke --dbname=${dbname} --file=loaddata.sql
${pgbindir}/psql --username=keisuke --dbname=${dbname} --file=createindex.sql

exit 0
