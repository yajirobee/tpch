#! /usr/bin/env python

import sys, os, glob, re, multiprocessing, sqlite3
import numpy as np
import drawio, drawcpu
from profileutils import get_ioprof, get_cpuprof, get_iocostprof

def proc_suffix(val, prefix):
    if 'k' == prefix:
        val *= 2 ** 10
    elif 'M' == prefix:
        val *= 2 ** 20
    elif 'G' == prefix:
        val *= 2 ** 30
    else:
        sys.stderr.write("wrong prefix\n")
        sys.exit(1)
    return val

def get_exectime(resfile):
    with open(resfile) as fo:
        i = 1
        step = 1 << 10
        while True:
            fo.seek(-1 * step * i, os.SEEK_END)
            buf = fo.read(step).rstrip()
            if "\n" in buf:
                fo.seek(-1 * step, os.SEEK_CUR)
                buf = fo.read().rstrip()
                return [float(v) for v in buf.rsplit("\n", 1)[1].split()]
            else:
                i += 1
    return None

def proc_iofile(iofile, devname):
    ioprof = get_ioprof(iofile, devname)
    output = "{0}.iohist".format(iofile.rsplit('.', 1)[0])
    with open(output, "w") as fo:
        for line in ioprof:
            fo.write('\t'.join([str(v) for v in line]) + "\n")
    ave = None
    if ioprof:
        ave = np.array(ioprof[0])
        for arr in ioprof[1:]:
            ave += arr
        for i in (0, 1, 6, 7, 8, 9, 10):
            ave[i] /= len(ioprof)
        ave = ave.tolist()
    return ave

def proc_cpufile(cpufile, corenum):
    cpuprof = get_cpuprof(cpufile, corenum)
    output = "{0}_core{1}.cpuhist".format(cpufile.rsplit('.', 1)[0], corenum)
    with open(output, "w") as fo:
        for line in cpuprof:
            fo.write('\t'.join([str(v) for v in line]) + "\n")
    ave = None
    if cpuprof:
        ave = np.array(cpuprof[0])
        for arr in cpuprof[1:]:
            ave += arr
        ave /= len(cpuprof)
        ave = ave.tolist()
    return ave

def proc_tracefile(iotracefile):
    iocostprof = get_iocostprof(iotracefile)
    statoutput = "{0}.iocosthist".format(iotracefile.rsplit('.', 1)[0])
    refoutput = "{0}.iorefhist".format(iotracefile.rsplit('.', 1)[0])
    fs = open(statoutput, "w")
    fr = open(refoutput, "w")
    for line in iocostprof:
        fs.write('\t'.join([str(v) for v in line[:-1]]) + "\n")
        fr.write(','.join(["{0}:{1}".format(k, v) for k, v in line[-1].items()]) + "\n")
    fs.close()
    fr.close()
    total = None
    if iocostprof:
        total = np.array(iocostprof[0][:-1])
        for arr in iocostprof[1:]:
            total += arr[:-1]
        total = total.tolist()
    return total

def proc_directory(directory, devname, corenum):
    sys.stdout.write("processing {0}\n".format(directory))
    match = re.search("workmem(\d+)(k|M|G)B", directory)
    workmem = proc_suffix(int(match.group(1)), match.group(2))
    sumio, sumcpu, sumiocost = None, None, None
    dirs = glob.glob(directory + "/*.time")
    if dirs:
        for f in dirs:
            exectime = float(open(f).readline().strip())
            #exectime = [float(v) for v in open(f).readline().strip().split()]
    else:
        for f in glob.iglob(directory + "/*.res"):
            exectime = get_exectime(f)
    for f in glob.iglob(directory + "/*.io"):
        sumio = proc_iofile(f, devname)
    for f in glob.iglob(directory + "/*.cpu"):
        sumcpu = proc_cpufile(f, corenum)
    dirs = glob.glob(directory + "/trace_*.log")
    if dirs:
        f = max(dirs, key = os.path.getsize)
        sumiocost = proc_tracefile(f)
    return workmem, exectime, sumio, sumcpu, sumiocost

def multiprocessing_helper(args):
    return args[0](*args[1:])

def main(rootdir, devname, corenum):
    ncore = multiprocessing.cpu_count() / 2
    pool = multiprocessing.Pool(ncore)
    dirs = []
    for d in glob.iglob(rootdir + "/workmem*"):
        dirs.extend(glob.glob(d + "/[0-9]*"))
    argslist = [(proc_directory, d, devname, corenum) for d in dirs]
    res = pool.map(multiprocessing_helper, argslist)

    conn = sqlite3.connect(rootdir + "/spec.db")
    maintbl = "measurement"
    maincols = ("id integer",
                "workmem integer",
                "exectime real")
    iostattbl = "io"
    iostatcols = ("id integer",
                  "rrpm_per_sec real",
                  "wrpm_per_sec real",
                  "total_readio real",
                  "total_writeio real",
                  "total_readmb real",
                  "total_writemb real",
                  "request_size real",
                  "queue_length real",
                  "wait_msec real",
                  "util real")
    cputbl = "cpu"
    cpucols = ("id integer",
               "usr real",
               "nice real",
               "sys real",
               "iowait real",
               "irq real",
               "soft real",
               "steal real",
               "guest real",
               "idle real")
    iotracetbl = "iotrace"
    iotracecols = ("id integer",
                   "readio_count integer",
                   "writeio_count integer",
                   "readio_nsec real",
                   "writeio_nsec real")
    tbldict = {maintbl : maincols,
               iostattbl : iostatcols,
               cputbl : cpucols,
               iotracetbl : iotracecols}
    for k, v in tbldict.items():
        conn.execute("create table {0} ({1})".format(k, ','.join(v)))
    for i, vals in enumerate(res):
        query = "insert into {0} values ({1})"
        conn.execute(query.format(maintbl, ','.join('?' * len(maincols))),
                     (i, vals[0], vals[1]))
        if vals[2]:
            vals[2].pop(9) # remove svctm column
            vals[2].insert(0, i)
            conn.execute(query.format(iostattbl, ','.join('?' * len(iostatcols))),
                         vals[2])
        if vals[3]:
            vals[3].insert(0, i)
            conn.execute(query.format(cputbl, ','.join('?' * len(cpucols))),
                         vals[3])
        if vals[4]:
            vals[4].insert(0, i)
            conn.execute(query.format(iotracetbl, ','.join('?' * len(iotracecols))),
                         vals[4])
        conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 4:
        rootdir = sys.argv[1]
        devname = sys.argv[2]
        corenum = sys.argv[3]
    else:
        sys.stderr.write(
            "Usage : {0} rootdir devname corenum\n".format(sys.argv[0]))
        sys.exit(0)

    main(rootdir, devname, corenum)
