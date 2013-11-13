#! /usr/bin/env python

import sys, os, glob, re, multiprocessing, sqlite3
import numpy as np
from dbprofutils import get_iocostprof

import drawio, drawcpu, profileutils

def proc_suffix(val, prefix):
    if 'k' == prefix: val *= 2 ** 10
    elif 'M' == prefix: val *= 2 ** 20
    elif 'G' == prefix: val *= 2 ** 30
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

def proc_iofile(iofile, devnames):
    iostatdict = profileutils.import_iostatfile(iofile)
    average = []
    for dev in devnames:
        ioprof = iostatdict.get(dev)
        if not ioprof: continue
        output = "{0}_{1}.iohist".format(os.path.splitext(iofile)[0], dev)
        with open(output, "w") as fo:
            for tup in ioprof: fo.write('\t'.join([str(v) for v in tup]) + "\n")
        ave = np.add.reduce(ioprof)
        ave /= len(ioprof)
        average.append(ave)
    if average:
        l = len(average)
        average = np.add.reduce(average)
        for i in (7, 8, 9, 10): average[i] /= l
    return average.tolist() if average != [] else None

def proc_cpufile(cpufile, corenums):
    cpustatdict = profileutils.import_mpstatfile(cpufile)
    average = []
    for core in corenums:
        cpuprof = cpustatdict.get(core)
        if not cpuprof: continue
        output = "{0}_core{1}.cpuhist".format(os.path.splitext(cpufile)[0], core)
        with open(output, "w") as fo:
            for tup in cpuprof: fo.write('\t'.join([str(v) for v in tup]) + "\n")
        ave = np.add.reduce(cpuprof)
        ave /= len(cpuprof)
        average.append(ave)
    if average:
        l = len(average)
        average = np.add.reduce(average)
    return average.tolist() if average != [] else None

def proc_statfile(statfile, corenums = None):
    columns = ("cycles", "cache_references", "cache_misses")
    if corenums:
        perfstatdict = profileutils.import_perfstatfile(statfile)
        total = []
        for core in corenums:
            cacheprof = perfstatdict.get(core)
            if not cacheprof: continue
            output = "{0}_core{1}.cachehist".format(os.path.splitext(statfile)[0], core)
            with open(output, "w") as fo:
                for dic in cacheprof:
                    fo.write('\t'.join(["{0}:{1}".format(k, v) for k, v in dic.items()]) + "\n")
            s = np.add.reduce([[d.get(col, 0) for col in columns] for d in cacheprof])
            total.append(s)
        return np.add.reduce(total).tolist() if total else None
    else:
        perfstatlist = profileutils.import_perfstatfile_aggregated(statfile)
        if not perfstatlist: return None
        output = "{0}.cachehist".format(os.path.splitext(statfile)[0])
        with open(output, "w") as fo:
            for dic in perfstatlist:
                fo.write("\t".join(["{0}:{1}".format(k, v) for k, v in dic.items()]) + "\n")
        return np.add.reduce([[d.get(col, 0) for col in columns] for d in perfstatlist]).tolist()

def proc_tracefile(iotracefile):
    iocostprof = get_iocostprof(iotracefile)
    fprefix = os.path.splitext(iotracefile)[0]
    statoutput = "{0}.iocosthist".format(fprefix)
    refoutput = "{0}.iorefhist".format(fprefix)
    with open(statoutput, "w") as fs, open(refoutput, "w") as fr:
        for line in iocostprof:
            fs.write('\t'.join([str(v) for v in line[:-1]]) + "\n")
            fr.write(','.join(["{0}:{1}".format(k, v) for k, v in line[-1].items()]) + "\n")
    return np.add.reduce([vals[:-1] for vals in iocostprof]).tolist() if iocostprof else None

def proc_directory(directory, devnames, corenums):
    sys.stdout.write("processing {0}\n".format(directory))
    match = re.search("workmem(\d+)(k|M|G)B", directory)
    workmem = proc_suffix(int(match.group(1)), match.group(2))
    sumio, sumcpu, sumiocost, sumcache = None, None, None, None
    dirs = glob.glob(directory + "/*.time")
    if dirs:
        for f in dirs: exectime = float(open(f).readline().strip())
        #for f in dirs: exectime = [float(v) for v in open(f).readline().strip().split()][4]
    else:
        for f in glob.iglob(directory + "/*.res"): exectime = get_exectime(f)
    for f in glob.iglob(directory + "/*.io"): sumio = proc_iofile(f, devnames)
    for f in glob.iglob(directory + "/*.cpu"): sumcpu = proc_cpufile(f, corenums)
    for f in glob.iglob(directory + "/*.perf"): sumcache = proc_statfile(f, corenums)
    dirs = glob.glob(directory + "/trace_*.log")
    if dirs:
        f = max(dirs, key = os.path.getsize)
        sumiocost = proc_tracefile(f)
    return workmem, exectime, sumio, sumcpu, sumiocost, sumcache

def multiprocessing_helper(args):
    return args[0](*args[1:])

def main(rootdir, devnames, corenums):
    ncore = multiprocessing.cpu_count() / 2
    pool = multiprocessing.Pool(ncore)
    dirs = []
    for d in glob.iglob(rootdir + "/workmem*"):
        dirs.extend(glob.glob(d + "/[0-9]*"))
    #res = [proc_directory(d, devnames, corenums) for d in dirs]
    argslist = [(proc_directory, d, devnames, corenums) for d in dirs]
    res = pool.map(multiprocessing_helper, argslist)


    # for d in dirs:
    #     proc_directory(d, devnames, corenums)

    conn = sqlite3.connect(rootdir + "/spec.db")
    maintbl = "measurement"
    maincols = ("id integer",
                "workmem integer",
                "exectime real")
    iostattbl = "io"
    iostatcols = ("id integer",
                  "rrpm_per_sec real",
                  "wrpm_per_sec real",
                  "average_readio real",
                  "average_writeio real",
                  "average_readmb real",
                  "average_writemb real",
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
    cachetbl = "cache"
    cachecols = ("id integer",
                 "cycles integer",
                 "cache_references integer",
                 "cache_misses integer")
    # cachecols = ("id integer",
    #              "all_cache_references integer",
    #              "L1D_cache_misses integer",
    #              "L2_cache_misses integer",
    #              "L3_cache_misses integer")
    tbldict = {maintbl : maincols,
               iostattbl : iostatcols,
               cputbl : cpucols,
               iotracetbl : iotracecols,
               cachetbl : cachecols}
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
        if vals[5]:
            vals[5].insert(0, i)
            conn.execute(query.format(cachetbl, ','.join('?' * len(cachecols))),
                         vals[5])
        conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 4:
        rootdir = sys.argv[1]
        devnames = sys.argv[2].split(',')
        corenums = sys.argv[3].split(',')
    else:
        sys.stderr.write(
            "Usage : {0} rootdir devnames corenums\n".format(sys.argv[0]))
        sys.exit(0)

    main(rootdir, devnames, corenums)
