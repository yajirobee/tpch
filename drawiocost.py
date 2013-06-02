#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil
from profileutils import get_iocostprof

interval = 10. ** 9

def plot_iocostprof(iocosthists, output, terminaltype):
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("I/O ratio [%]")
    gp('set grid front')
    gds = []
    gds.append(Gnuplot.Data(range(len(iocosthists[0])),
                            [v / interval for v in iocosthists[0]],
                            with_ = "lines",
                            title = "Read"))
    gds.append(Gnuplot.Data(range(len(iocosthists[1])),
                            [v / interval for v in iocosthists[1]],
                            with_ = "lines",
                            title = "Write"))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        iotracefile = sys.argv[1]
        terminaltype = "png"
    elif len(sys.argv) == 3:
        iotracefile = sys.argv[1]
        terminaltype = sys.argv[2]
    else:
        sys.stdout.write("Usage : {0} iotracefile [png|eps]\n".format(sys.argv[0]))
        sys.exit(0)

    iocosthists = get_iocostprof(iotracefile)
    sys.stdout.write(
        ("total read I/O time : {0} [sec]\n"
         "total write I/O time : {1} [sec]\n"
         .format(sum(iocosthists[0]) / interval,
                 sum(iocosthists[1]) / interval)))
    fprefix = iotracefile.rsplit('.', 1)[0]
    output = "{0}iocosthist.{1}".format(fprefix, terminaltype)
    plot_iocostprof(iocosthists, output, terminaltype)
