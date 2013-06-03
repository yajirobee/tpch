#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil
from profileutils import get_reliddict, get_tblrefprof

def plot_tblrefhist(reliddict, refhist, output, terminaltype = "png"):
    rellist = []
    for d in refhist:
        for k in d:
            if k not in rellist and k > 3000:
                rellist.append(k)

    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("count [pages]")
    #gp('set key outside')
    gp('set grid front')
    gp('set style fill pattern 1 border')
    gd = []
    xlen = len(refhist)
    piledatas = [[] for i in range(len(rellist))]
    for d in refhist:
        for i, relid in enumerate(rellist):
            if i == 0:
                piledatas[i].append(d.get(relid, 0))
            else:
                piledatas[i].append(piledatas[i - 1][-1] + d.get(relid, 0))
    gd = []
    for i, relid in enumerate(rellist):
        if i == 0:
            gd.append(Gnuplot.Data(range(xlen), piledatas[i],
                                   with_ = "filledcurve x1", title = reliddict[relid]))
        else:
            gd.append(Gnuplot.Data(range(xlen), piledatas[i], piledatas[i - 1],
                                   with_ = "filledcurve", title = reliddict[relid]))
    gp.plot(*gd)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        iodumpfile = sys.argv[1]
        relidfile = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        iodumpfile = sys.argv[1]
        relidfile = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stdout.write(
            "Usage : {0} iodumpfile relidfile [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    reliddict = get_reliddict(relidfile)
    refhist = get_tblrefprof(iodumpfile)

    fprefix = iodumpfile.rsplit('.', 1)[0]
    fpath = "{0}refhist.{1}".format(fprefix, terminaltype)
    plot_tblrefhist(reliddict, refhist, fpath, terminaltype)
