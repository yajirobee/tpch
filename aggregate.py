#! /usr/bin/env python

import sys, os, glob, re, multiprocessing, sqlite3
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
        for line in zip(*ioprof):
            fo.write('\t'.join([str(v) for v in line]) + "\n")
    return sum(ioprof[0]), sum(ioprof[1])

def proc_cpufile(cpufile, corenum):
    cpuprof = get_cpuprof(cpufile, corenum)
    output = "{0}_core{1}.cpuhist".format(cpufile.rsplit('.', 1)[0], corenum)
    with open(output, "w") as fo:
        for line in cpuprof:
            fo.write('\t'.join([str(v) for v in line]) + "\n")

def proc_tracefile(iotracefile):
    iocostprof = get_iocostprof(iotracefile)
    output = "{0}.iocosthist".format(iotracefile.rsplit('.', 1)[0])
    with open(output, "w") as fo:
        for line in zip(*iocostprof):
            fo.write('\t'.join([str(v) for v in line]) + "\n")
    return sum(iocostprof[0]), sum(iocostprof[1])


def proc_directory(devname, corenum, directory):
    sys.stdout.write("processing {0}\n".format(directory))
    match = re.search("workmem(\d+)(k|M|G)B", directory)
    workmem = proc_suffix(int(match.group(1)), match.group(2))
    for f in glob.iglob(directory + "/*.res"):
        exectime = get_exectime(f)
    for f in glob.iglob(directory + "/*.io"):
        rsum, wsum = proc_iofile(f, devname)
    for f in glob.iglob(directory + "/*.cpu"):
        proc_cpufile(f, corenum)
    f = max(glob.glob(directory + "/trace_*.log"), key = os.path.getsize)
    riocostsum, wiocostsum = proc_tracefile(f)
    return workmem, exectime[4], rsum, wsum, riocostsum, wiocostsum

def multiprocessing_helper(args):
    return args[0](*args[1:])

def main(rootdir, devname, corenum):
    conn = sqlite3.connect(rootdir + "/spec.db")
    ncore = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(ncore)
    dirs = []
    for d in glob.iglob(rootdir + "/workmem*"):
        dirs.extend(glob.glob(d + "/[0-9]*"))

    tblname = "execspec"
    columns = ("workmem integer",
               "exectime real",
               "readio integer",
               "writeio integer",
               "readiocost real",
               "writeiocost real")
    conn.execute("create table {0} ({1})".format(tblname, ','.join(columns)))

    argslist = [(proc_directory, d, devname, corename) for d in dirs]
    for vals in pool.map(multiprocessing_helper, argslist):
        conn.execute(("insert into {0} values ({1})"
                      .format(tblname, ','.join('?' * len(columns)))),
                     vals)
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
