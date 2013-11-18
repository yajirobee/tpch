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
    db = "tpch"
    dbs = ["tpch{0}".format(i) for i in range(64)]
    #db = "tpchdisk"
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
        # {"select": "r1cb", "name": "MEM_LOAD_RETIRED.L1D_HIT"},
        # {"select": "r40cb", "name": "MEM_LOAD_RETIRED.HIT_LFB"},
        # {"select": "r2cb", "name": "MEM_LOAD_RETIRED.L2_HIT"},
        # {"select": "r4cb", "name": "MEM_LOAD_RETIRED.LLC_UNSHARED_HIT"},
        # {"select": "r8cb", "name": "MEM_LOAD_RETIRED.OTHER_CORE_L2_HIT_HITM"},
        # {"select": "r10cb", "name": "MEM_LOAD_RETIRED.LLC _MISS"},
        # {"select": "r80cb", "name": "MEM_LOAD_RETIRED.DTLB_MISS"},
        # {"select": "r39", "name": "UNC_LLC_MISS.ANY"},
        # {"select": "raa24", "name": "L2_RQSTS.MISS"},
        )
    perfcmd = ("perf stat -a -A -e "
               "cycles,cache-references,cache-misses,"
               "faults,minor-faults,major-faults,"
               "LLC-loads,LLC-load-misses,"
               "LLC-stores,LLC-store-misses "
               "-o {0} --append -- ")
    # perfcmd = ("perf record -a -g -q -e cache-references -f -o {0} -- ")

    profflg = True
    iotraceflg = False
    perfflg = True

    def __init__(self, queryfile):
        self.fprefix = os.path.splitext(os.path.basename(queryfile))[0]
        self.query = ' '.join([line.strip().split("--", 1)[0]
                               for line in open(qfile, "rU")]).strip()
        self.confdict = {}
        self.pgproc = None
        self.pglogfile = open(os.path.join(self.dbdatadir + "pgserver.log"), "a")

    def output_queryplan(self, destdir):
        # output query execution plan
        exppath = os.path.join(destdir, self.fprefix + ".exp")
        sp.call([self.pgbindir + "psql", "-d", self.dbs[0], "-Ukeisuke",
                 "-c", 'explain ' + self.query],
                stdout = open(exppath, "w"))

    def restart_db(self, destdir):
        user = sp.Popen(["whoami"], stdout = sp.PIPE).stdout.read().strip()
        # stop postgres
        if self.pgproc:
            self.pgproc.send_signal(signal.SIGINT)
            time.sleep(5)
        if os.path.exists(self.dbdatadir + "postmaster.pid"):
            pgstopcmd = ("{0}/pg_ctl stop -D {datadir} -m fast"
                         .format(self.pgbindir, datadir = self.dbdatadir))
            if "root" == user: pgstopcmd = ["su", "keisuke", "-c", pgstopcmd]
            else: pgstopcmd = shlex.split(pgstopcmd)
            sp.call(pgstopcmd)
            time.sleep(5)
        # clear cache
        clear_cache(2 ** 33)
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
        if "root" == user: pgstartcmd = ["su", "keisuke", "-c", ' '.join(pgstartcmd)]
        self.pgproc = sp.Popen(pgstartcmd,
                               stdout = self.pglogfile,
                               stderr = self.pglogfile)
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
        if self.perfflg:
            cmd = shlex.split(self.perfcmd.format(perfout)) + cmd
        count = 0
        elapsed = []
        while count < 3:
            self.restart_db(destdir)
            self.output_queryplan(destdir)
            sys.stdout.write("query started\n")
            if self.iotraceflg:
                pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpuout, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(ioout, "w"))
            try:
                # run query
                fo = open(resfile, "w")
                stime = monotonic_time()
                rcode = sp.call(cmd, stdout = fo)
                ftime = monotonic_time()
                sys.stdout.write("query finished\n")
                elapsed = ftime - stime
                with open(timefile, "w") as ft:
                    ft.write("{0}\n".format(elapsed))
                if not rcode:
                    break
                else:
                    count += 1
                    sys.stderr.write("Query Execution Error : {0}\n".format(rcode))
                    time.sleep(5)
            finally:
                fo.close()
                if self.profflg:
                    pio.kill()
                    pcpu.kill()
                if self.iotraceflg:
                    pbt.kill()
        return elapsed

    def run_query_wperf(self, destdir, interval = 1):
        outputprefix = os.path.join(destdir, self.fprefix)
        resfile = outputprefix + ".res"
        timefile = outputprefix + ".time"
        ioout = outputprefix + ".io"
        cpuout = outputprefix + ".cpu"
        perfout = outputprefix + ".perf"
        cmd = [self.pgbindir + "psql", "-d", self.db, "-Ukeisuke", "-c", self.query]
        perfcmd = self.perfcmd.format(perfout) + "sleep {0}".format(interval)
        perfcmd = shlex.split(perfcmd)
        count = 0
        elapsed = []
        while count < 3:
            self.restart_db(destdir)
            self.output_queryplan(destdir)
            sys.stdout.write("query started\n")
            if self.iotraceflg:
                pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpuout, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(ioout, "w"))
            try:
                # run query
                fo = open(resfile, "w")
                pid = os.fork()
                if pid == 0:
                    while True: sp.call(perfcmd)
                    # t = 0
                    # perfout = "{0}/{1}_{{0}}.perf".format(destdir, self.fprefix)
                    # perfcmd = self.perfcmd + "sleep {0}".format(interval)
                    # while True:
                    #     sp.call(shlex.split(perfcmd.format(perfout.format(t))))
                    #     t += interval
                else:
                    stime = monotonic_time()
                    rcode = sp.call(cmd, stdout = fo)
                    ftime = monotonic_time()
            finally:
                os.kill(pid, 9)
                fo.close()
                if self.profflg:
                    pio.kill()
                    pcpu.kill()
                if self.iotraceflg:
                    pbt.kill()
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

    def run_multiquery_wperf(self, destdir, nquery, interval = 1):
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
                   #"--cpu=" + ','.join([str(v) for v in self.cpus]),
                   "--output", perfout, "--append",
                   "--event=" + ','.join([d["select"] for d in self.perfevents]),
                   "sleep", str(interval)]
        count = 0
        elapsed = []
        while count < 3:
            self.restart_db(destdir)
            self.output_queryplan(destdir)
            sys.stdout.write("query started\n")
            if self.iotraceflg:
                pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpuout, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(ioout, "w"))
            try:
                # run query
                fos = [open(f, "w") for f in resfiles]
                pid = os.fork()
                if pid == 0:
                    while True: sp.call(perfcmd)
                    # t = 0
                    # perfout = "{0}/{1}_{{0}}.perf".format(destdir, self.fprefix)
                    # perfcmd = self.perfcmd + "sleep {0}".format(interval)
                    # while True:
                    #     sp.call(shlex.split(perfcmd.format(perfout.format(t))))
                    #     t += interval
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
                if self.iotraceflg:
                    pbt.kill()
        return elapsed

iteration = 5

def main(qfile):
    outdir = "/data/local/keisuke/tpch/" +  time.strftime("%Y%m%d%H%M%S", time.gmtime())
    os.mkdir(outdir)
    qr = query_runner(qfile)
    sys.stdout.write("Query :\n{0}\n".format(qr.query))

    for i in range(iteration):
        destdir = "{0}/{1}".format(outdir, i)
        #destdir = "{0}/{1}disk".format(outdir, i)
        os.mkdir(destdir)
        sys.stdout.write("Execution count : {0}\n".format(i))
        elapsed = qr.run_query(destdir)

def main2(qfile, nquery):
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
        # "1GB",
        # "2GB",
        # "4GB",
        # "8GB"
        ]

    #workmemlist = ["{0}MB".format(v) for v in range(16, 33)]

    user = sp.Popen(["whoami"], stdout = sp.PIPE).stdout.read().strip()
    for i in range(iteration):
        for j, workmem in enumerate(workmemlist):
            qr.confdict["-S"] = workmem
            destdir = "{0}/workmem{1}/{2}".format(outdir, workmem, i)
            os.makedirs(destdir)
            if "root" == user: os.chmod(destdir, 0777)
            sys.stdout.write(
                "Execution count : {0} (work_mem = {1})\n".format(i, workmem))
            elapsed = qr.run_multiquery_wperf(destdir, nquery)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        qfile = sys.argv[1]
    else:
        sys.stdout.write("Usage : {0} queryfile\n".format(sys.argv[0]))
        sys.exit(1)

    #for i in range(4, 7): main2(qfile, 1 << i)
    main2(qfile, 64)
