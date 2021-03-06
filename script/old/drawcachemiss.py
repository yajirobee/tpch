#! /usr/bin/env python

import sys, os, glob, re, Gnuplot
import plotutil

def plot_cachemiss(cacheprof, output, terminaltype = "png"):
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel('elapsed time [s]')
    gp('set ytics nomirror')
    gp('set ylabel "count" offset 4')
    gp('set y2label "cache miss rate [%]" offset -2')
    gp('set grid xtics noytics noy2tics')
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
    plotprefdict = {"with_" : "lines"}
    gds.append(Gnuplot.Data(xlist, cacheref,
                            title = "cache reference", axes = "x1y1",
                            **plotprefdict))
    gds.append(Gnuplot.Data(xlist, cachemiss,
                            title = "cache miss", axes = "x1y1",
                            **plotprefdict))
    gds.append(Gnuplot.Data(xlist, cachemissrate,
                            title = "cache miss rate", axes = "x1y2",
                            **plotprefdict))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

def plot_cachemiss_new(cacheprof, output, terminaltype = "png"):
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel('elapsed time [s]')
    gp('set ytics nomirror')
    gp('set ylabel "count" offset 4')
    gp('set y2label "rate [%]" offset -2')
    gp('set grid xtics noytics noy2tics')
    gp('set yrange [0:*]')
    gp('set y2range [0:100]')
    gp('set y2tic 10')
    gds = []
    xaxis = []
    y1axes = [{"name": "all cache ref", "values": []},
              {"name": "L1D cache miss", "values": []},
              {"name": "L2 cache miss", "values": []},
              {"name": "L3 cache miss", "values": []}]
    y2axes = [{"name": "L1D cache miss rate", "values": []},
              {"name": "L2 cache miss rate", "values": []},
              {"name": "L3 cache miss rate", "values": []}]
    for v in cacheprof:
        xaxis.append(v[0])
        for i, axis in enumerate(y1axes): axis["values"].append(v[i + 1])
        for i, axis in enumerate(y2axes): axis["values"].append(float(v[i + 2]) / v[i + 1] * 100)
    plotprefdict = {"with_" : "lines"}
    for axis in y1axes:
        gds.append(Gnuplot.Data(xaxis, axis["values"],
                                title = axis["name"], axes = "x1y1",
                                **plotprefdict))
    for axis in y2axes:
        gds.append(Gnuplot.Data(xaxis, axis["values"],
                                title = axis["name"], axes = "x1y2",
                                **plotprefdict))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write(
            "Usage : {0} statfile core [terminaltype]\n".format(sys.argv[0]))
        sys.exit(0)

    statfile = sys.argv[1]
    core = sys.argv[2]
    terminaltype = sys.argv[3] if len(sys.argv) >= 4 else "png"

    from profileutils import get_cacheprof
    cacheprof = get_cacheprof(statfile, core)
    output = "{0}core{1}.{2}".format(statfile.rsplit('.', 1)[0], core, terminaltype)
    plot_cachemiss(cacheprof, output, terminaltype)
