#! /usr/bin/env python

import sys, os, gnuplot

terminaltype = "png"
if terminaltype == "eps":
    settermcmd = 'set terminal postscript eps color "Times-Roman,26"'
elif terminaltype == "png":
    settermcmd = "set terminal png"
else:
    sys.stdout.write("wrong terminal type\n")
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stdout.write("Usage : {0} filepath\n".format(sys.argv[0]))
        sys.exit(0)

    fpath = sys.argv[1]
    data = []
    for line in fpath:
        k, v = line.split(None, 1)
        if k == "md0":
            data.append(float(v[4]))

    gp = Gnuplot.Gnuplot()
    gp(settermcmd)
    gp.xlabel("elapsed time(s)")
    gp.ylabel("num of read sector")
    gd = Gnuplot.Data(range(len(data)), data, with_ = "linespoints")
    gp.plot(gd)
