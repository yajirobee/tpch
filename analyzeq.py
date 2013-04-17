#! /usr/bin/env python

import sys, os, glob, re, Gnuplot
import drawio, drawcpu, plotutil

def analyzeq(inputdir, devname = "md0", corenum = "1", terminaltype = "png"):
    eladict = {}
    for d in glob.iglob(inputdir + "/workmem*"):
        avefile = d + "/average.txt"
        vals = open(avefile).read().split()
        match = re.search("workmem(\d+)(k|M|G)B", d)
        size = int(match.group(1))
        prefix = match.group(2)
        if prefix == 'k':
            size *= 2 ** 10
        elif prefix == 'M':
            size *= 2 ** 20
        elif prefix == 'G':
            size *= 2 ** 30
        else:
            sys.stderr.write("wrong prefix\n")
            sys.exit(1)
        eladict[size] = vals
        for dd in glob.iglob(d + "/[0-9]*"):
            ioprofiler = drawio.ioprofiler(devname)
            for f in glob.iglob(dd + "/*.io"):
                ioprof = ioprofiler.get_ioprof(f)
                outprefix = f.rsplit('.', 1)[0] + d.rsplit("/", 1)[1]
                drawio.plot_ioprof(ioprof, outprefix, terminaltype)
            for f in glob.iglob(dd + "/*.cpu"):
                coreutil = drawcpu.get_cpuprof(f, corenum)
                output = f.rsplit('.', 1)[0] + d.rsplit("/", 1)[1]
                output += "core" + corenum + "." + terminaltype
                drawcpu.plot_cpuprof(coreutil, output, terminaltype)
    elalist = sorted(eladict.items(), key = lambda x:int(x[0]))
    gp = plotutil.gpinit(terminaltype)
    output = inputdir + "/elapsed." + terminaltype
    gp('set output "{0}"'.format(inputdir + "/elapsed." + terminaltype))
    gp.xlabel("workmem (B)")
    gp.ylabel("elapsed time (s)")
    gp('set grid')
    gp('set logscale x')
    gd = Gnuplot.Data([int(v[0]) for v in elalist], [float(v[1][4]) for v in elalist], with_ = "linespoints")
    gp.plot(gd)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        inputdir = sys.argv[1]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        inputdir = sys.argv[1]
        terminaltype = sys.argv[2]
    else:
        sys.stdout.write(
            "Usage : {0} inputdir [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    analyzeq(inputdir)
