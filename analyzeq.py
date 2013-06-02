#! /usr/bin/env python

import sys, os, glob, re, Gnuplot
import drawio, drawcpu, plotutil

iospecdict = {"md0" : {"seqread" : 1294, "randread" : 318, "randwrite" : 1000},
              "sdb" : {"seqread" : 385, "randread" : 100, "randwrite" : 300}}

restrictflg = True
slide = False

def analyzeq(inputdir, devname = "md0", corenum = "1", terminaltype = "png"):
    eladict = {}
    iodict = {}
    for d in glob.iglob(inputdir + "/workmem*"):
        elapsed = []
        io = []
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
        for dd in glob.iglob(d + "/[0-9]*"):
            ioprofiler = drawio.ioprofiler(devname)
            for f in glob.iglob(dd + "/*.io"):
                ioprof = ioprofiler.get_ioprof(f)
                io.append((sum(ioprof[0]), sum(ioprof[1])))
                if restrictflg:
                    continue
                outprefix = f.rsplit('.', 1)[0] + d.rsplit("/", 1)[1]
                drawio.plot_ioprof(ioprof, outprefix, terminaltype)
            for f in glob.iglob(dd + "/*.cpu"):
                if restrictflg:
                    continue
                coreutil = drawcpu.get_cpuprof(f, corenum)
                output = f.rsplit('.', 1)[0] + d.rsplit("/", 1)[1]
                output += "core" + corenum + "." + terminaltype
                drawcpu.plot_cpuprof(coreutil, output, terminaltype)
            for f in glob.iglob(dd + "/*.res"):
                with open(f) as fo:
                    i = 1
                    step = 1 << 10
                    while True:
                        fo.seek(-1 * step * i, os.SEEK_END)
                        buf = fo.read(step).rstrip()
                        if "\n" in buf:
                            elapsed.append([float(v) for v in buf.rsplit("\n", 1)[1].split()])
                            break
        ela = elapsed[0]
        for e in elapsed[1:]:
            for i in range(len(ela)):
                ela[i] += e[i]
        for i in range(len(ela)):
            ela[i] /= len(elapsed)
        eladict[size] = ela
        r = [v[0] for v in io]
        w = [v[1] for v in io]
        iodict[size] = (sum(r) / len(r), sum(w) / len(w))

    gp = plotutil.gpinit(terminaltype)
    output = inputdir + "/elapsed." + terminaltype
    gp('set output "{0}"'.format(inputdir + "/elapsed." + terminaltype))
    gp.xlabel("working memory")
    gp.ylabel("Execution time [s]")
    gp('set grid')
    gp('set logscale x')
    gp('set format x "%.0s%cB"')
    gp('set xrange [10000:*]')
    gp('set yrange [0:1800]')
    if slide:
        if "eps" == terminaltype:
            gp('set termoption font "Times-Roman,28"')
            plotprefdict = {"with_" : "linespoints lt 1 lw 6" }
        elif "png" == terminaltype:
            gp('set termoption font "Times-Roman,20"')
            plotprefdict = {"with_" : "linespoints lt 1 lw 4"}
    else:
        plotprefdict = {"with_" : "linespoints" }
    elalist = sorted(eladict.items(), key = lambda x:int(x[0]))
    gd = Gnuplot.Data([int(v[0]) for v in elalist],
                      [float(v[1][4]) for v in elalist],
                      title = "Execution time",
                      **plotprefdict)
    seqio = (86. + 20 + 3 + 3) * 1024 + 173
    seqcost = seqio / iospecdict[devname]["seqread"]
    iocostlist = []
    for k, v in sorted(iodict.items(), key = lambda x:int(x[0])):
        cost = (seqcost
                + (v[0] - seqio) / iospecdict[devname]["randread"]
                + v[1] / iospecdict[devname]["randwrite"])
        iocostlist.append((k, cost))
    gdio = Gnuplot.Data([int(v[0]) for v in iocostlist],
                        [v[1] for v in iocostlist],
                        [int(v[0]) / 4 for v in iocostlist],
                        title = "Estimated I/O cost",
                        with_ = 'boxes fs solid border lc rgb "black"')
                        #with_ = "linespoints lc 2 lt 1 lw 6")
    #gp("set key right center")
    gp.plot(gd, gdio)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        inputdir = sys.argv[1]
        dev = "md0"
        terminaltype = "png"
    elif len(sys.argv) == 3:
        inputdir = sys.argv[1]
        dev = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        inputdir = sys.argv[1]
        dev = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stdout.write(
            "Usage : {0} inputdir [dev] [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    analyzeq(inputdir, dev, "1", terminaltype)
