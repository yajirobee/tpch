#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil
from profileutils import get_ioprof

slide = False

def plot_ioprof(ioprof, outprefix, terminaltype = "png"):
    rmbps, wmbps, riops, wiops, ioutil = ioprof
    gp = plotutil.gpinit(terminaltype)
    gp.xlabel("elapsed time [s]")
    gp('set grid')
    if slide:
        gp('set termoption font "Times-Roman,22"')

    # draw mbps graph
    output = "{0}mbps.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("MBps")
    gp.ylabel("I/O throughput [MB/s]")
    if slide:
        gdrmbps = Gnuplot.Data(range(len(rmbps)), rmbps,
                               with_ = "lines lw 2", title = "read")
                           #with_ = "lines", title = "read MBps")
        gdwmbps = Gnuplot.Data(range(len(wmbps)), wmbps,
                               with_ = "lines lw 2 lc 3", title = "write")
    else:
        gdrmbps = Gnuplot.Data(range(len(rmbps)), rmbps,
                               with_ = "lines", title = "read")
        gdwmbps = Gnuplot.Data(range(len(wmbps)), wmbps,
                               with_ = "lines", title = "write")
    gp.plot(gdrmbps, gdwmbps)
    sys.stdout.write("output {0}\n".format(output))

    # draw iops graph
    output = "{0}iops.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("I/O throughput [IO/s]")
    gdriops = Gnuplot.Data(range(len(riops)), riops,
                           with_ = "lines", title = "read")
    gdwiops = Gnuplot.Data(range(len(wiops)), wiops,
                           with_ = "lines", title = "write")
    gp.plot(gdriops, gdwiops)
    sys.stdout.write("output {0}\n".format(output))

    # draw iosize graph
    output = "{0}iosize.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("iosize [KB]")
    rios = [(rmb * 1000.) / rio if rio != 0 else 0.
            for rmb, rio in zip(rmbps, riops)]
    wios = [(wmb * 1000) / wio if wio != 0 else 0.
            for wmb, wio in zip(wmbps, wiops)]
    gdrios = Gnuplot.Data(range(len(rios)), rios,
                          with_ = "lines", title = "read iosize")
    gdwios = Gnuplot.Data(range(len(wios)), wios,
                          with_ = "lines", title = "write iosize")
    gp.plot(gdrios, gdwios)
    sys.stdout.write("output {0}\n".format(output))

    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        iofile = sys.argv[1]
        devname = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        iofile = sys.argv[1]
        devname = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stdout.write(
            "Usage : {0} iostatfile devname [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    ioprof = get_ioprof(iofile, devname)
    outprefix = iofile.rsplit('.', 1)[0]

    plot_ioprof(ioprof, outprefix, terminaltype)
