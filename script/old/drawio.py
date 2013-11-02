#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil

slide = False

def plot_ioprof(ioprof, outprefix, terminaltype = "png"):
    riops, wiops, rmbps, wmbps, riosize, wiosize = [[] for i in range(6)]
    t = len(ioprof)
    for vals in ioprof:
        riops.append(vals[2])
        wiops.append(vals[3])
        rmbps.append(vals[4])
        wmbps.append(vals[5])
        riosize.append((vals[4] * 1000.) / vals[2] if vals[2] != 0 else 0.)
        wiosize.append((vals[5] * 1000.) / vals[3] if vals[3] != 0 else 0.)
    gp = plotutil.gpinit(terminaltype)
    gp.xlabel("elapsed time [s]")
    gp('set grid')
    if slide:
        gp('set termoption font "Times-Roman,22"')
        plotprefdict = {"with_" : "lines lw 2"}
    else:
        plotprefdict = {"with_" : "lines"}

    # draw mbps graph
    output = "{0}mbps.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("MBps")
    gp.ylabel("I/O throughput [MB/s]")
    gp('set yrange [0:*]')
    gdrmbps = Gnuplot.Data(range(t), rmbps, title = "Read", **plotprefdict)
    gdwmbps = Gnuplot.Data(range(t), wmbps, title = "Write", **plotprefdict)
    gp.plot(gdrmbps, gdwmbps)
    sys.stdout.write("output {0}\n".format(output))

    # draw iops graph
    output = "{0}iops.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("I/O throughput [IO/s]")
    gdriops = Gnuplot.Data(range(t), riops, title = "Read", **plotprefdict)
    gdwiops = Gnuplot.Data(range(t), wiops, title = "Write", **plotprefdict)
    gp.plot(gdriops, gdwiops)
    sys.stdout.write("output {0}\n".format(output))

    # draw iosize graph
    output = "{0}iosize.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("I/O size [KB]")
    gdrios = Gnuplot.Data(range(t), riosize, title = "Read", **plotprefdict)
    gdwios = Gnuplot.Data(range(t), wiosize, title = "Write", **plotprefdict)
    gp.plot(gdrios, gdwios)
    sys.stdout.write("output {0}\n".format(output))

    gp.close()

def readiofile(iofile):
    ioprof = [[float(v) for v in line.strip().split()] for line in open(iofile)]
    return ioprof

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stdout.write(
            "Usage : {0} iostatfile devname [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    iofile = sys.argv[1]
    devname = sys.argv[2] if len(sys.argv) >= 3 else None
    terminaltype = sys.argv[3] if len(sys.argv) >= 4 else "png"
    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    if len(sys.argv) == 2: ioprof = readiofile(iofile)
    else:
        from profileutils import get_ioprof
        ioprof = get_ioprof(iofile, devname)

    outprefix = iofile.rsplit('.', 1)[0]

    plot_ioprof(ioprof, outprefix, terminaltype)
