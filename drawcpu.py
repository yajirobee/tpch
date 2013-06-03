#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil
from profileutils import get_cpuprof

keys = ("usr", "nice", "sys", "iowait", "irq", "soft", "steal", "guest", "idle")

def plot_cpuprof(cpuprof, output, terminaltype = "png"):
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("util [%]")
    gp('set yrange [0:100]')
    gp('set key outside')
    gp('set grid front')
    gp('set style fill pattern 1 border')
    gd = []
    xlen = len(cpuprof)
    piledatas = [[] for i in range(len(keys))]
    for vals in cpuprof:
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
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        cpufile = sys.argv[1]
        core = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        cpufile = sys.argv[1]
        core = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stdout.write(
            "Usage : {0} mpstatfile core [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    cpuprof = get_cpuprof(cpufile, core)

    fprefix = cpufile.rsplit('.', 1)[0]
    output = "{0}core{1}.{2}".format(fprefix, core, terminaltype)
    plot_cpuprof(cpuprof, output, terminaltype)
