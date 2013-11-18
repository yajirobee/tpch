#! /usr/bin/env python

import sys, os, subprocess, shlex, time

outdir = "/data/local/keisuke/tpch"
psqlcmd = "psql -d tpch -U keisuke"
#psqlcmd = "psql -d tpchdisk -U keisuke"

varname = "custkeymax"
#vals = [10 ** i for i in range(2, 7)] + [15000000] + [20000, 40000, 60000, 80000]
vals = [10000]
vdicts = [{varname : v} for v in vals]

if __name__ == "__main__":
    if len(sys.argv) == 2:
        qfile = sys.argv[1]
    else:
        sys.stdout.write("Usage : {0} queryfile\n".format(sys.argv[0]))
        sys.exit(1)

    fprefix = os.path.basename(qfile).rsplit('.', 1)[0]
    query = ' '.join([line.strip().split("--", 1)[0] for line in open(qfile, "rU")]).strip()

    for vdict in vdicts:
        distdir = "{0}/{1}_{2}".format(outdir, fprefix,
                                       '_'.join([str(k) + str(v) for k, v in vdict.items()]))
        #distdir = "{0}/{1}disk_{2}".format(outdir, fprefix,
        #                               '_'.join([str(k) + str(v) for k, v in vdict.items()]))
        os.mkdir(distdir)
        q = query.format(**vdict)
        cmd = psqlcmd + " -c " + '"' + q + '"'
        sys.stdout.write("Execute : {0}\n".format(cmd))
        exppath = "{0}/{1}.exp".format(distdir, fprefix)
        cpupath = "{0}/{1}.cpu".format(distdir, fprefix)
        iopath = "{0}/{1}.io".format(distdir, fprefix)
        resfile = "{0}/{1}.res".format(distdir, fprefix)
        # clear storage side buffer
        ppool = []
        readcmd = "/data/local/keisuke/local/bin/sequentialread /dev/fio{0}2 {1} {2} {3}"
        for i in "abcdefgh":
            ppool.append(subprocess.Popen(shlex.split(readcmd.format(i, 2 ** 28, 32, 4)), stdout = open("/dev/null", "w")))
        for p in ppool:
            if p.wait() != 0:
                sys.stderr.write("iodrive read error : {0}\n".format(p.pid))
                sys.exit(1)
        # output query execution plan
        subprocess.call(shlex.split(psqlcmd + " -c " + '"' + "explain " + q + '"'),
                        stdout = open(exppath, "w"))
        subprocess.call(shlex.split("pg stop"))
        time.sleep(3)
        subprocess.call(shlex.split("pg start"))
        time.sleep(3)
        # clear cache
        subprocess.call(["clearcache"])
        # run mpstat and iostat
        pcpu = subprocess.Popen(shlex.split("mpstat -P ALL 1"),
                                stdout = open(cpupath, "w"))
        pio = subprocess.Popen(shlex.split("iostat -x 1"),
                               stdout = open(iopath, "w"))
        # run query
        with open(resfile, "w") as fo:
            stime = os.times()
            rcode = subprocess.call(shlex.split(cmd), stdout = fo)
            ftime = os.times()
            fo.write("\n{0}\n".format(' '.join([str(f - s) for f, s in zip(ftime, stime)])))
        pio.kill()
        pcpu.kill()
        if rcode:
            sys.stderr.write("Query Execution Error\n")
