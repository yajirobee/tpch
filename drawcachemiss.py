#! /usr/bin/env python

import sys, os, glob, re, Gnuplot
import plotutil

def plot_cachemiss(cacheprof, output, terminaltype = "png"):
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel('elapsed time [s]')
    gp.ylabel('count')
    gp('set ytics nomirror')
    gp('set y2label "cache miss rate [%]"')
    gp('set yrange [0:*]')
    gp('set y2range [0:100]')
    gp('set y2tic 10')
    gds = []
    xlist, cacheref, cachemiss, cachemissrate = [], [], [], []
    for v in cacheprof:
        xlist.append(v[0])
        cacheref.append(v[2])
        cachemiss.append(v[3])
        cachemissrate.append((float(v[3]) / v[2]) * 100)
    gds.append(Gnuplot.Data(xlist, cacheref,
                            title = "cache reference",
                            axes = "x1y1", with_ = "lines"))
    gds.append(Gnuplot.Data(xlist, cachemiss,
                            title = "cache miss",
                            axes = "x1y1", with_ = "lines"))
    gds.append(Gnuplot.Data(xlist, cachemissrate,
                            title = "cache miss rate",
                            axes = "x1y2", with_ = "lines"))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        statfile = sys.argv[1]
        core = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        statfile = sys.argv[1]
        core = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stderr.write(
            "Usage : {0} statfile core [terminaltype]\n".format(sys.argv[0]))
        sys.exit(0)

    from profileutils import get_cacheprof
    cacheprof = get_cacheprof(statfile, core)
    output = "{0}core{1}.{2}".format(statfile.rsplit('.', 1)[0], core, terminaltype)
    plot_cachemiss(cacheprof, output, terminaltype)
