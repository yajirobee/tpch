#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil

interval = 10. ** 9

def plot_iocostprof(iocostprof, output, terminaltype):
    riocost, wiocost = [], []
    t = len(iocostprof)
    for vals in iocostprof:
        riocost.append(vals[2] / interval)
        wiocost.append(vals[3] / interval)
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("I/O ratio [%]")
    gp('set grid front')
    gds = []
    gds.append(Gnuplot.Data(range(t), riocost, title = "Read", with_ = "lines"))
    gds.append(Gnuplot.Data(range(t), wiocost, title = "Write", with_ = "lines"))
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

    from profileutils import get_iocostprof
    iocostprof = get_iocostprof(iotracefile)
    fprefix = iotracefile.rsplit('.', 1)[0]
    output = "{0}iocosthist.{1}".format(fprefix, terminaltype)
    plot_iocostprof(iocostprof, output, terminaltype)
