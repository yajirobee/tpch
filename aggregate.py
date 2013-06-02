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

def proc_iofile(iofile, devname, terminaltype = None):
    ioprof = get_ioprof(iofile, devname)
    if terminaltype:
        outprefix = iofile.rsplit('.', 1)[0]
        outprefix += os.path.basename(os.path.dirname(os.path.dirname(iofile)))
        drawio.plot_ioprof(ioprof, outprefix, terminaltype)
    return sum(ioprof[0]), sum(ioprof[1])

def proc_cpufile(cpufile, corenum, terminaltype = None):
    cpuprof = get_cpuprof(cpufile, corenum)
    if terminaltype:
        output = cpufile.rsplit('.', 1)[0]
        output += os.path.basename(os.path.dirname(os.path.dirname(cpufile)))
        output += "core" + corenum + "." + terminaltype
        drawcpu.plot_cpuprof(cpuprof, output, terminaltype)

def proc_tracefile(iotracefile, terminaltype = None):
    iocosthists = get_iocostprof(iotracefile)
    if terminaltype:
        fprefix = iotracefile.rsplist('.', 1)[0]
        output = "{0}iocosthist.{1}".format(fprefix, terminaltype)
        drawiocost.plot_iocostprof(iocosthists, output, terminaltype)
    return sum(iocosthists[0]), sum(iocosthists[1])

def proc_directory_wrapper(devname, corenum, terminaltype):
    def proc_directory(directory):
        match = re.search("workmem(\d+)(k|M|G)B", directory)
        workmem = proc_suffix(int(match.group(1)), match.group(2))
        for f in glob.iglob(directory + "/*.res"):
            exectime = get_exectime(f)
        for f in glob.iglob(directory + "/*.io"):
            rsum, wsum = proc_iofile(f, devname, terminaltype)
        for f in glob.iglob(directory + "/*.cpu"):
            proc_cpufile(f, corenum, terminaltype)
        f = max(glob.glob(directory + "/trace_*.log"), key = os.path.getsize)
        riocostsum, wiocostsum = proc_tracefile(f, terminaltype)
        return workmem, exectime, rsum, wsum, riocostsum, wiocostsum
    return proc_directory

def main(rootdir, devname, corenum, terminaltype):
    conn = sqlite3.connect(rootdir + "/spec.db")
    ncore = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(ncore)
    dirs = []
    for d in glob.iglob(rootdir + "/workmem*"):
        dirs.extend(glob.glob(d + "[0-9]*"))

    tblname = "execspec"
    columns = ("workmem integer",
               "exectime real",
               "readio integer",
               "writeio integer",
               "readiocost real",
               "writeiocost real")
    conn.execute("create table {0} ({1})".format(tblname, ','.join(columns)))

    for vals in pool.map(
        proc_directory_wrapper(devname, corenum, terminaltype), dirs):
        conn.execute(("insert into {0} values ({1})"
                      .format(tblname, ','.join('?' * len(columns)))),
                     vals)
        self.conn.commit()

if __name__ == "__main__":
    if len(sys.argv) == 4:
        rootdir = sys.argv[1]
        devname = sys.argv[2]
        corenum = sys.argv[3]
        terminaltype = "png"
    elif len(sys.argv) == 5:
        rootdir = sys.argv[1]
        devname = sys.argv[2]
        corenum = sys.argv[3]
        terminaltype = sys.argv[4]
    else:
        sys.stderr.write(
            "Usage : {0} rootdir devname corenum [png|eps]\n".format(sys.argv[0]))
        sys.exit(0)

    main(rootdir, devname, corenum, terminaltype)
