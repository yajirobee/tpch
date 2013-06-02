#! /usr/bin/env python

import sys, os, glob, re, multiprocessing, sqlite3
import drawio, drawcpu
from profileutils import get_ioprof, get_cpuprof

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

def proc_iofile_wrapper(devname, terminaltype):
    def proc_iofile(directory):
        for f in glob.iglob(d + "/*.io"):
            ioprof = get_ioprof(f, devname)
            outprefix = f.rsplit('.', 1)[0] + os.path.basename(os.path.dirname(directory))
            drawio.plot_ioprof(ioprof, outprefix, terminaltype)
    return proc_iofile

def proc_cpufile_wrapper(corenum, terminaltype):
    def proc_cpufile(directory):
        for f in glob.iglob(d + "/*.cpu"):
            cpuprof = get_cpuprof(f, corenum)
            output = f.rsplit('.', 1)[0] + os.path.basename(os.path.dirname(directory))
            output += "core" + corenum + "." + terminaltype
            drawcpu.plot_cpuprof(coreutil, output, terminaltype)
    return proc_cpufile

def get_exectime(directory):
    for f in glob.iglob(dd + "/*.res"):
        with open(f) as fo:
            i = 1
            step = 1 << 10
            while True:
                fo.seek(-1 * step * i, os.SEEK_END)
                buf = fo.read(step).rstrip()
                if "\n" in buf:
                    fo.seek(-1 * step, os.SEEK_CUR)
                    buf = fo.read().rstrip()
                    return [float(v) for v in buf.rsplit("\n", 1)[1].split()])
                else:
                    i += 1
    return None

def main(rootdir, devname, terminaltype):
    conn = sqlite3.connect(rootdir + "spec.db")
    ncore = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(ncore)
    dirs = []
    for d in glob.iglob(rootdir + "/workmem*"):
        dirs.extend(glob.glob(d + "[0-9]*"))

    tblname = 
    conn.execute("create table {0} ()".format(tblname))
    for vals in pool.map(proc_iofile_wrapper(devname, terminaltype), dirs):
        pass

    tblname = 
    conn.execute("create table {0} ()".format(tblname))
    for vals in pool.map(proc_cpufile_wrapper(corenum, terminaltype), dirs):
        pass

    tblname = 
    conn.execute("create table {0} ()".format(tblname))
    for vals in pool.map(get_exectime, dirs):
        pass

if __name__ == "__main__":
