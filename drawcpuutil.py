#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil

utilcol = 2

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stdout.write(
            "Usage : {0} mpstatfile [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    cpuproffile = sys.argv[1]
    terminaltype = sys.argv[2] if len(sys.argv) >= 3 else "png"
    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    from profileutils import get_allcpuprof
    sysutil = get_allcpuprof(cpuproffile, utilcol)

    fprefix = cpuproffile.rsplit('.', 1)[0]
    gp = plotutil.gpinit(terminaltype)
    fpath = "{0}util.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("util [%]")
    gdcpu = Gnuplot.Data(range(len(sysutil)), sysutil,
                          with_ = "lines", title = "cpuutil")
    gp.plot(gdcpu)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()
