#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil
from profileutils import get_iocostprof

interval = 10. ** 9

def plot_iocostprof(iocostprof, output, terminaltype):
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("I/O ratio [%]")
    gp('set grid front')
    gds = []
    gds.append(Gnuplot.Data(range(len(iocostprof[0])),
                            [v / interval for v in iocostprof[0]],
                            with_ = "lines",
                            title = "Read"))
    gds.append(Gnuplot.Data(range(len(iocostprof[1])),
                            [v / interval for v in iocostprof[1]],
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

    iocostprof = get_iocostprof(iotracefile)
    sys.stdout.write(
        ("total read I/O time : {0} [sec]\n"
         "total write I/O time : {1} [sec]\n"
         .format(sum(iocostprof[0]) / interval,
                 sum(iocostprof[1]) / interval)))
    fprefix = iotracefile.rsplit('.', 1)[0]
    output = "{0}iocosthist.{1}".format(fprefix, terminaltype)
    plot_iocostprof(iocostprof, output, terminaltype)
