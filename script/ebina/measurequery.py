#! /usr/bin/env python

import sys, os, shlex, time, signal, glob
import subprocess as sp
from monotonic import monotonic_time
from clearcache import *

sys.path.append("/home/keisuke/git/systemprofiletools/scripts/common")
import util

class query_runner(object):
    cpus = [1]
    pgbindir = "/data/local/keisuke/local/bin/"
    #pgbindir = "/data/local/keisuke/local/pgtest/bin/"
    #db = "tpch"
    db = "tpchdisk"
    dbs = ["tpch{0}".format(i) for i in range(64)]
    dbdatadir = "/data/local/keisuke/pgdata/"

    perfevents = (
        {"select": "cycles", "name": "cycles"},
        {"select": "cache-references", "name": "L3_cache_references"},
        {"select": "cache-misses", "name": "L3_cache_misses"},
        {"select": "LLC-loads", "name": "LLC-loads"},
        {"select": "LLC-load-misses", "name": "LLC-load-misses"},
        {"select": "LLC-stores", "name": "LLC-stores"},
        {"select": "LLC-store-misses", "name": "LLC-store-misses"},
        {"select": "L1-dcache-loads", "name": "L1-dcache-loads"},
        {"select": "L1-dcache-load-misses", "name": "L1-dcache-load-misses"},
        {"select": "L1-dcache-stores", "name": "L1-dcache-stores"},
        {"select": "L1-dcache-store-misses", "name": "L1-dcache-store-misses"},
        )

    profflg = True
    iotraceflg = False

    def __init__(self, queryfile, interval = 1):
        self.fprefix = os.path.splitext(os.path.basename(queryfile))[0]
        self.query = ' '.join([line.strip().split("--", 1)[0]
                               for line in open(qfile, "rU")]).strip()
        self.confdict = {}
        self.pgproc = None
        self.pglogfile = open(os.path.join(self.dbdatadir + "pgserver.log"), "a")
        self.user = sp.Popen(["whoami"], stdout = sp.PIPE).stdout.read().strip()
        self.interval = interval

    def output_queryplan(self, db, destdir):
        # output query execution plan
        exppath = os.path.join(destdir, self.fprefix + ".exp")
        sp.call([self.pgbindir + "psql", "-d", db, "-Ukeisuke",
                 "-c", 'explain ' + self.query],
                stdout = open(exppath, "w"))

    def restart_db(self, destdir):
        # stop postgres
        if self.pgproc:
            self.pgproc.send_signal(signal.SIGINT)
            time.sleep(5)
        if os.path.exists(self.dbdatadir + "postmaster.pid"):
            pgstopcmd = ("{0}/pg_ctl stop -D {datadir} -m fast"
                         .format(self.pgbindir, datadir = self.dbdatadir))
            if "root" == self.user: pgstopcmd = ["su", "keisuke", "-c", pgstopcmd]
            else: pgstopcmd = shlex.split(pgstopcmd)
            sp.call(pgstopcmd)
            time.sleep(5)
        # clear cache
        clear_os_cache()
        #clear_iodrive_buffer(2 ** 33)
        clear_disk_buffer(2 ** 28)
        # start postgres
        pgstartcmd = ["env", "PGTRACE=" + destdir,
                      "numactl", "--physcpubind=" + ','.join([str(v) for v in self.cpus]),
                      "--", self.pgbindir + "postgres", "-D", self.dbdatadir,
                      #"--enable-iotracer=on",
                      #"--enable-buckettracer=on"
                      ]
        for k, v in self.confdict.items():
            pgstartcmd.append(str(k))
            if v: pgstartcmd.append(str(v))
        if "root" == self.user: pgstartcmd = ["su", "keisuke", "-c", ' '.join(pgstartcmd)]
        self.pgproc = sp.Popen(pgstartcmd, stdout = self.pglogfile, stderr = self.pglogfile)
        time.sleep(10)
        if not os.path.exists(self.dbdatadir + "postmaster.pid"):
            sys.stderr.write("postgres start failed\n")
            sys.exit(1)

    def run_query(self, destdir):
        outputprefix = os.path.join(destdir, self.fprefix)
        resfile = outputprefix + ".res"
        timefile = outputprefix + ".time"
        ioout = outputprefix + ".io"
        cpuout = outputprefix + ".cpu"
        perfout = outputprefix + ".perf"
        cmd = [self.pgbindir + "psql", "-d", self.db, "-Ukeisuke", "-c", self.query]
        count, elapsed = 0, 0
        while count < 3:
            self.restart_db(destdir)
            self.output_queryplan(self.db, destdir)
            sys.stdout.write("query started\n")
            if self.iotraceflg: pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpuout, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(ioout, "w"))
            fo = open(resfile, "w")
            try:
                # run query
                stime = monotonic_time()
                rcode = sp.call(cmd, stdout = fo)
                ftime = monotonic_time()
                sys.stdout.write("query finished\n")
                elapsed = ftime - stime
                with open(timefile, "w") as ft:
                    ft.write("{0}\n".format(elapsed))
                if not rcode: break
                else:
                    count += 1
                    sys.stderr.write("Query Execution Error : {0}\n".format(rcode))
                    time.sleep(5)
            finally:
                fo.close()
                if self.profflg:
                    pio.kill()
                    pcpu.kill()
                if self.iotraceflg: pbt.kill()
        return elapsed

    def run_query_wperf(self, destdir):
        outputprefix = os.path.join(destdir, self.fprefix)
        resfile = outputprefix + ".res"
        timefile = outputprefix + ".time"
        ioout = outputprefix + ".io"
        cpuout = outputprefix + ".cpu"
        perfout = outputprefix + ".perf"
        cmd = [self.pgbindir + "psql", "-d", self.db, "-Ukeisuke", "-c", self.query]
        perfcmd = ["perf", "stat", "--all-cpus", "--no-aggr",
                   "--output", perfout, "--append",
                   "--event=" + ','.join([d["select"] for d in self.perfevents]),
                   "sleep", str(self.interval)]
        count, elapsed = 0, 0
        while count < 3:
            self.restart_db(destdir)
            self.output_queryplan(self.db, destdir)
            sys.stdout.write("query started\n")
            if self.iotraceflg: pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpuout, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(ioout, "w"))
            fo = open(resfile, "w")
            pid = os.fork()
            # run query
            if pid == 0:
                while True: sp.call(perfcmd)
            else:
                try:
                    stime = monotonic_time()
                    rcode = sp.call(cmd, stdout = fo)
                    ftime = monotonic_time()
                finally:
                    os.kill(pid, 9)
                    fo.close()
                    if self.profflg:
                        pio.kill()
                        pcpu.kill()
                    if self.iotraceflg: pbt.kill()
            sys.stdout.write("query finished\n")
            elapsed = ftime - stime
            with open(timefile, "w") as ft:
                ft.write("{0}\n".format(elapsed))
            if not rcode: break
            else:
                count += 1
                sys.stderr.write("Query Execution Error : {0}\n".format(rcode))
                time.sleep(5)
        return elapsed

    def run_multiquery_wperf(self, destdir, nquery):
        self.cpus = range(min(nquery, 32))
        outputprefix = os.path.join(destdir, self.fprefix)
        resfiles = [outputprefix + "_{0}.res".format(i) for i in range(nquery)]
        timefile = outputprefix + ".time"
        perfout = outputprefix + ".perf"
        ioout = outputprefix + ".io"
        cpuout = outputprefix + ".cpu"
        cmds = [[self.pgbindir + "psql", "-d", db, "-Ukeisuke", "-c", self.query]
                for db in self.dbs[:nquery]]
        perfcmd = ["perf", "stat", "--all-cpus", "--no-aggr",
                   "--output", perfout, "--append",
                   "--event=" + ','.join([d["select"] for d in self.perfevents]),
                   "sleep", str(self.interval)]
        count, elapsed = 0, 0
        while count < 3:
            self.restart_db(destdir)
            self.output_queryplan(self.dbs[0], destdir)
            sys.stdout.write("query started\n")
            if self.iotraceflg: pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpuout, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(ioout, "w"))
            fos = [open(f, "w") for f in resfiles]
            try:
                # run query
                pid = os.fork()
                if pid == 0:
                    while True: sp.call(perfcmd)
                else:
                    stime = monotonic_time()
                    procs = [sp.Popen(cmd, stdout = fo) for cmd, fo in zip(cmds, fos)]
                    rcs = [p.wait() for p in procs]
                    ftime = monotonic_time()
                    os.kill(pid, 9)
                sys.stdout.write("query finished\n")
                elapsed = ftime - stime
                with open(timefile, "w") as ft:
                    ft.write("{0}\n".format(elapsed))
                if [0 for rc in rcs] == rcs: break
                else:
                    count += 1
                    sys.stderr.write("Query Execution Error : Errorcodes{0}\n".format(rcs))
                    time.sleep(5)
            finally:
                for fo in fos: fo.close()
                if self.profflg:
                    pio.kill()
                    pcpu.kill()
                if self.iotraceflg: pbt.kill()
        return elapsed

def main(qfile, nquery = None):
    iteration = 5
    outdir = "/data/local/keisuke/tpch/" +  time.strftime("%Y%m%d%H%M%S", time.gmtime())
    os.mkdir(outdir)
    qr = query_runner(qfile)
    #qr.confdict["--enable-iotracer=on"] = None
    sys.stdout.write("Query :\n{0}\n".format(qr.query))

    workmemlist = [
        "64kB",
        "128kB",
        "256kB",
        "512kB",
        "1MB",
        "2MB",
        "4MB",
        "8MB",
        "16MB",
        # "24MB",
        "32MB",
        "64MB",
        "128MB",
        "256MB",
        "512MB",
        "1GB",
        "2GB",
        # "4GB",
        # "8GB"
        ]
    for i in range(iteration):
        for j, workmem in enumerate(workmemlist):
            qr.confdict["-S"] = workmem
            destdir = "{0}/workmem{1}/{2}".format(outdir, workmem, i)
            os.makedirs(destdir)
            if "root" == qr.user: os.chmod(destdir, 0777)
            sys.stdout.write("Execution count : {0} (work_mem = {1})\n".format(i, workmem))
            if nquery != None: elapsed = qr.run_multiquery_wperf(destdir, nquery)
            else: elapsed = qr.run_query_wperf(destdir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stdout.write("Usage : {0} queryfile\n".format(sys.argv[0]))
        sys.exit(1)

    qfile = sys.argv[1]
    main(qfile)
    #for i in range(4, 7): main(qfile, 1 << i)
