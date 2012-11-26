#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil

utilcol = 2

datepat = re.compile(r"\d{2}:\d{2}:\d{2}")
floatpat = re.compile(r"\d+(?:\.\d*)?|\.\d+")

def get_cpuprof(fpath):
    sysutil = []
    util = 0.
    date = None
    for line in open(fpath):
        val = line.split()
        if not val or val[1] == "all" or val[1] == "CPU":
            continue
        elif date != val[0] and datepat.search(val[0]):
            if date:
                sysutil.append(util)
            date = val[0]
            util = 0.
        if floatpat.search(val[utilcol]):
            coreutil = float(val[utilcol])
            if coreutil > 3.0:
                util += coreutil
    return sysutil

if __name__ == "__main__":
    if len(sys.argv) == 2:
        cpuproffile = sys.argv[1]
        terminaltype = "png"
    elif len(sys.argv) == 3:
        cpuproffile = sys.argv[1]
        terminaltype = sys.argv[2]
    else:
        sys.stdout.write(
            "Usage : {0} mpstatfile [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    sysutil = get_cpuprof(cpuproffile)

    fprefix = cpuproffile.rsplit('.', 1)[0]
    gp = plotutil.gpinit(terminaltype)
    fpath = "{0}util.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("util(%)")
    gdcpu = Gnuplot.Data(range(len(sysutil)), sysutil,
                          with_ = "lines", title = "cpuutil")
    gp.plot(gdcpu)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()
