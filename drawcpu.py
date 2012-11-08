#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil

terminaltype = "png"
if terminaltype != "png" and terminaltype != "eps":
    sys.stdout.write("wrong terminal type\n")
    sys.exit(1)

def get_cpuprof(fpath, core):
    coreutil = []
    for line in open(fpath):
        val = line.split()
        if not val:
            continue
        elif val[1] == core:
            coreutil.append([float(v) for v in val[2:]])
    return coreutil

keys = ("usr", "nice", "sys", "iowait", "irq", "soft", "steal", "guest", "idle")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stdout.write("Usage : {0} cpuproffile core\n".format(sys.argv[0]))
        sys.exit(0)

    cpufile = sys.argv[1]
    core = sys.argv[2]
    coreutil = get_cpuprof(cpufile, core)

    fprefix = cpufile.rsplit('.', 1)[0]
    gp = plotutil.gpinit(terminaltype)
    fpath = "{0}core{1}.{2}".format(fprefix, core, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("util(%)")
    gp('set yrange [0:100]')
    gp('set key outside')
    gp('set grid front')
    gp('set style fill pattern 1 border')
    gd = []
    xlen = len(coreutil)
    piledatas = [[] for i in range(len(keys))]
    for vals in coreutil:
        piledatas[0].append(vals[0])
        for i in range(1, len(keys)):
            piledatas[i].append(piledatas[i - 1][-1] + vals[i])
    gd = []
    gd.append(Gnuplot.Data(range(xlen), piledatas[0],
                           with_ = "filledcurve x1", title = keys[0]))
    for i in range(1, len(keys)):
        gd.append(Gnuplot.Data(range(xlen), piledatas[i], piledatas[i - 1],
                               with_ = "filledcurve", title = keys[i]))
    gp.plot(*gd)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()
