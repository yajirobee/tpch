#! /usr/bin/env python

import sys, os, shlex, time, signal, glob
import subprocess as sp
import psycopg2 as pg
from psycopg2 import errorcodes
from monotonic import monotonic_time
from clearcache import *

class query_runner(object):
    pgbindir = "/data/local/keisuke/local/bin/"
    #pgbindir = "/data/local/keisuke/local/pgtest/bin/"
    db = "tpch"
    #db = "tpchdisk"
    dbs = ["tpch", "tpch2", "tpch3", "tpch4"]
    user = "keisuke"
    dbdatadir = "/data/local/keisuke/pgdata/"
    confpath = dbdatadir + "postgresql.conf"

    perfcmd = ("perf stat -p {pid} -e "
               "cycles,cache-references,cache-misses,"
               "faults,minor-faults,major-faults,"
               "LLC-loads,LLC-load-misses,"
               "LLC-stores,LLC-store-misses "
               "-o {output} --append"
               )
    #perfcmd = ("perf record -p {pid} -g -q -e cache-references -f -o {output} -- ")

    profflg = True
    iotraceflg = False
    perfflg = True

    def __init__(self, queryfile):
        self.fprefix = os.path.basename(queryfile).rsplit('.', 1)[0]
        self.query = ' '.join([line.strip().split("--", 1)[0]
                               for line in open(qfile, "rU")]).strip()
        self.confdict = {}
        self.pgproc = None
        self.pglogfile = open(self.dbdatadir + "/pgserver.log", "a")

    def restart_db(self, destdir):
        # stop postgres
        if self.pgproc:
            self.pgproc.send_signal(signal.SIGINT)
            time.sleep(10)
        if os.path.exists(self.dbdatadir + "postmaster.pid"):
            pgstopcmd = ("{0}/pg_ctl stop -D {datadir} -m fast"
                         .format(self.pgbindir, datadir = self.dbdatadir))
            sp.call(shlex.split(pgstopcmd))
            time.sleep(10)
        # clear cache
        #clear_cache(2 ** 33)
        # start postgres
        pgstartcmd = ["env", "PGTRACE=" + destdir,
                      "numactl", "--physcpubind=1-4", "--",
                      self.pgbindir + "postgres", "-D", self.dbdatadir,
                      #"--enable-iotracer=on"
                      ]
        for k, v in self.confdict.items():
            pgstartcmd.append(str(k))
            if v:
                pgstartcmd.append(str(v))
        user = sp.Popen(["whoami"], stdout = sp.PIPE).stdout.read().strip()
        if "root" == user: pgstartcmd = ["su", "keisuke", "-c", ' '.join(pgstartcmd)]
        self.pgproc = sp.Popen(pgstartcmd,
                               stdout = self.pglogfile,
                               stderr = self.pglogfile)
        time.sleep(10)
        if not os.path.exists(self.dbdatadir + "postmaster.pid"):
            sys.stderr.write("postgres start failed\n")
            sys.exit(1)

    def run_query_wperf(self, destdir):
        # define output file names
        exppath = "{0}/{1}.exp".format(destdir, self.fprefix)
        resfile = "{0}/{1}.res".format(destdir, self.fprefix)
        timefile = "{0}/{1}.time".format(destdir, self.fprefix)
        perfpath = "{0}/{1}.perf".format(destdir, self.fprefix)
        if self.profflg:
            cpupath = "{0}/{1}.cpu".format(destdir, self.fprefix)
            iopath = "{0}/{1}.io".format(destdir, self.fprefix)

        count = 0
        finishflg = False
        while not finishflg and count < 3:
            self.restart_db(destdir)
            # create db connection
            conn = pg.connect(database = self.db, user = self.user)
            cur = conn.cursor()

            # output execution plan
            cur.execute("explain " + self.query)
            with open(exppath, "w") as fo:
                fo.writelines([vals[0] + "\n" for vals in cur.fetchall()])

            # get backend pid
            cur.execute("select pg_backend_pid()")
            pgpid = cur.fetchone()[0]

            sys.stdout.write("query started: trycount {0}\n".format(count))
            if self.iotraceflg:
                pbt = sp.Popen(["blktrace", "/dev/md0", "-D", destdir])
            if self.profflg:
                # run mpstat and iostat
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpupath, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(iopath, "w"))

            try:
                # run query
                pid = os.fork()
                if 0 == pid:
                    # perf process
                    cmd = shlex.split(self.perfcmd.format(pid = pgpid, output = perfpath))
                    p = sp.Popen(cmd)
                    def stopperf(signum, frame):
                        os.kill(p.pid, signal.SIGINT)
                        ret = p.wait()
                        print ret, open(perfpath).readlines()
                        os.kill(os.getpid(), signal.SIGKILL)
                    signal.signal(signal.SIGINT, stopperf)
                    p.wait()
                else:
                    stime = monotonic_time()
                    cur.execute(self.query)
                    ftime = monotonic_time()
                    os.kill(pid, signal.SIGINT)
                sys.stdout.write("query finished\n")
                finishflg = True
            except pg.Error, e:
                errstate = errorcodes.lookup(e.pgcode)
                sys.stderr.write("query execution failed: {0}\n".format(errstate))
                count += 1
                time.sleep(5)
                continue
            except Exception, e:
                sys.stderr.write("query execution failed: {0}\n".format(e.message))
                count += 1
                time.sleep(5)
                continue
            finally:
                if self.profflg:
                    pio.kill()
                    pcpu.kill()
                if self.iotraceflg:
                    pbt.kill()
            elapsed = ftime - stime
            with open(timefile, "w") as ft:
                ft.write("{0}\n".format(elapsed))
            with open(resfile, "w") as fo:
                fo.write('\t'.join([str(vals[0]) for vals in cur.description]) + "\n\n")
                vals = cur.fetchone()
                while vals:
                    fo.write('\t'.join([str(v) for v in vals]) + "\n")
                    vals = cur.fetchone()
        return elapsed

    def run_multiquery_wperf(self, destdir, nquery, interval = 5):
        # define output file names
        resfiles = ["{0}/{1}_{2}.res".format(destdir, self.fprefix, i) for i in range(nquery)]
        timefile = "{0}/{1}.time".format(destdir, self.fprefix)
        if self.profflg:
            cpupath = "{0}/{1}.cpu".format(destdir, self.fprefix)
            iopath = "{0}/{1}.io".format(destdir, self.fprefix)

        cmds = [[self.pgbindir + "psql", "-d", db, "-Ukeisuke", "-c", self.query]
                for db in self.dbs[:nquery]]
        perfpath = "{0}/{1}.perf".format(destdir, self.fprefix)
        perfcmd = self.perfcmd.format(perfpath) + "sleep {0}".format(interval)
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
                pcpu = sp.Popen(["mpstat", "-P", "ALL", "1"], stdout = open(cpupath, "w"))
                pio = sp.Popen(["iostat", "-x", "1"], stdout = open(iopath, "w"))
            try:
                # run query
                fos = [open(f, "w") for f in resfiles]
                pid = os.fork()
                if pid == 0:
                    while True: sp.call(perfcmd)
                    # t = 0
                    # perfpath = "{0}/{1}_{{0}}.perf".format(destdir, self.fprefix)
                    # perfcmd = self.perfcmd + "sleep {0}".format(interval)
                    # while True:
                    #     sp.call(shlex.split(perfcmd.format(perfpath.format(t))))
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


outdir = "/data/local/keisuke/tpch/" +  time.strftime("%Y%m%d%H%M%S", time.gmtime())
os.mkdir(outdir)
iteration = 5

def main(qfile):
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
            elapsed = qr.run_query_wperf(destdir)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        qfile = sys.argv[1]
    else:
        sys.stdout.write("Usage : {0} queryfile\n".format(sys.argv[0]))
        sys.exit(1)

    main(qfile)
