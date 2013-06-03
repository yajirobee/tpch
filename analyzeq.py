#! /usr/bin/env python

import sys, os, glob, re, Gnuplot
import drawio, drawcpu, drawiocost, drawioref
from profileutils import get_reliddict
from plotutil import query2data, gpinit

slide = True

def get_iocosts(iodict):
    iospecdict = {"md0" : {"seqread" : 1294, "randread" : 318, "randwrite" : 1000},
                  "sdb" : {"seqread" : 385, "randread" : 100, "randwrite" : 300}}
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
    return iocostlist

def gen_allgraph(rootdir, reliddict = None, terminaltype = "png"):
    for d in glob.iglob(rootdir + "/workmem*"):
        for dd in glob.iglob(d + "/[0-9]*"):
            outprefix = dd + "/default"
            for f in glob.iglob(dd + "/*.res"):
                outprefix = f.rsplit('.', 1)[0] + os.path.basename(d)
            for f in glob.iglob(dd + "/*.iohist"):
                ioprof = []
                for line in open(f):
                    ioprof.append([float(v) for v in line.strip().split()])
                drawio.plot_ioprof(ioprof, outprefix, terminaltype)
            for f in glob.iglob(dd + "/*.cpuhist"):
                cpuprof = []
                for line in open(f):
                    cpuprof.append([float(v) for v in line.strip().split()])
                output = f.rsplit('.', 1)[0] + os.path.basename(d)
                output += "." + terminaltype
                drawcpu.plot_cpuprof(cpuprof, output, terminaltype)
            for f in glob.iglob(dd + "/trace_*.iocosthist"):
                iocostprof = []
                for line in open(f):
                    iocostprof.append([float(v) for v in line.strip().split()])
                output = "{0}iocosthist.{1}".format(outprefix, terminaltype)
                drawiocost.plot_iocostprof(iocostprof, output, terminaltype)
            if reliddict:
                for f in glob.iglob(dd + "/trace_*.iorefhist"):
                    iorefhist = []
                    for line in open(f):
                        dic = {}
                        line = line.strip()
                        if line:
                            for word in line.split(','):
                                k, v = word.split(':', 1)
                                dic[int(k)] = int(v)
                        iorefhist.append(dic)
                    output = "{0}iorefhist.{1}".format(outprefix, terminaltype)
                    drawioref.plot_tblrefhist(reliddict, iorefhist, output, terminaltype)

def plot_workmem_exectime(dbpath, output, terminaltype = "png"):
    gp = gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("working memory")
    gp.ylabel("Time [s]")
    gp('set grid')
    gp('set logscale x')
    gp('set format x "%.0s%cB"')
    gp('set xrange [10000:*]')
    #gp('set yrange [0:1800]')
    if slide:
        gp('set key right center')
        if "eps" == terminaltype:
            gp('set termoption font "Times-Roman,28"')
            plotprefdict = {"with_" : "linespoints lt 1 lw 6" }
        elif "png" == terminaltype:
            gp('set termoption font "Times-Roman,18"')
            plotprefdict = {"with_" : "linespoints lw 2"}
    else:
        plotprefdict = {"with_" : "linespoints" }
    query = ("select workmem, avg({y}) from execspec "
             "group by workmem order by workmem")
    gdexec = query2data(dbpath, query.format(y = "exectime"),
                        title = "Execution time", **plotprefdict)[0]
    query = ("select workmem, avg({y})/1000000000 from execspec "
             "group by workmem order by workmem")
    gdrio, gdwio = query2data(dbpath, query, y = ("readiocost", "writeiocost"),
                              title = "{y}", **plotprefdict)
    gdio = query2data(dbpath, query.format(y = "readiocost + writeiocost"),
                      title = "I/O cost", **plotprefdict)[0]
    query = ("select workmem, avg(exectime - (readiocost + writeiocost) / 1000000000) "
             "from execspec group by workmem order by workmem")
    gdexecwoio = query2data(dbpath, query,
                            title = "CPU cost", **plotprefdict)[0]
    gp.plot(gdexec, gdrio, gdwio, gdio, gdexecwoio)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

def plot_workmem_io(dbpath, output, terminaltype = "png"):
    gp = gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("working memory")
    gp.ylabel("I/O size [MB]")
    gp('set grid')
    gp('set logscale x')
    gp('set format x "%.0s%cB"')
    gp('set xrange [10000:*]')
    #gp('set yrange [0:1800]')
    gp('set key right center')
    if slide:
        if "eps" == terminaltype:
            gp('set termoption font "Times-Roman,28"')
            plotprefdict = {"with_" : "linespoints lt 1 lw 6" }
        elif "png" == terminaltype:
            gp('set termoption font "Times-Roman,20"')
            plotprefdict = {"with_" : "linespoints lw 2"}
    else:
        plotprefdict = {"with_" : "linespoints" }
    query = ("select workmem, avg({y}) from execspec "
             "group by workmem order by workmem")
    gdr = query2data(dbpath, query.format(y = "readio"),
                     title = "Read", **plotprefdict)[0]
    gdw = query2data(dbpath, query.format(y = "writeio"),
                     title = "Write", **plotprefdict)[0]
    gp.plot(gdr, gdw)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

def plot_workmem_iocount(dbpath, output, terminaltype):
    gp = gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("working memory")
    gp.ylabel("I/O count")
    gp('set grid')
    gp('set logscale x')
    gp('set format x "%.0s%cB"')
    gp('set xrange [10000:*]')
    #gp('set yrange [0:1800]')
    gp('set key right center')
    if slide:
        if "eps" == terminaltype:
            gp('set termoption font "Times-Roman,28"')
            plotprefdict = {"with_" : "linespoints lt 1 lw 6" }
        elif "png" == terminaltype:
            gp('set termoption font "Times-Roman,20"')
            plotprefdict = {"with_" : "linespoints lw 2"}
    else:
        plotprefdict = {"with_" : "linespoints" }
    query = ("select workmem, avg({y}) from execspec "
             "group by workmem order by workmem")
    gdr = query2data(dbpath, query.format(y = "readiocount"),
                     title = "Read", **plotprefdict)[0]
    gdw = query2data(dbpath, query.format(y = "writeiocount"),
                     title = "Write", **plotprefdict)[0]
    gp.plot(gdr, gdw)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        rootdir = sys.argv[1]
        relidfile = None
        terminaltype = "png"
    elif len(sys.argv) == 3:
        rootdir = sys.argv[1]
        relidfile = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        rootdir = sys.argv[1]
        relidfile = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stderr.write(
            "Usage : {0} rootdir [relidfile] [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stderr.write("wrong terminal type\n")
        sys.exit(1)

    reliddict = get_reliddict(relidfile) if relidfile else None
    gen_allgraph(rootdir, reliddict, terminaltype)
    output = "{0}/exectime.{1}".format(rootdir, terminaltype)
    plot_workmem_exectime(rootdir + "/spec.db", output, terminaltype)
    output = "{0}/io.{1}".format(rootdir, terminaltype)
    plot_workmem_io(rootdir + "/spec.db", output, terminaltype)
    output = "{0}/iocount.{1}".format(rootdir, terminaltype)
    plot_workmem_iocount(rootdir + "/spec.db", output, terminaltype)
