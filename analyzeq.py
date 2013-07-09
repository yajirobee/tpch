#! /usr/bin/env python

import sys, os, glob, re, Gnuplot, sqlite3
import drawio, drawcpu, drawiocost, drawioref, drawcachemiss
import numpy as np
from profileutils import get_reliddict
from plotutil import query2data, query2gds, gpinit

slide = False
xlogplot = True

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
            for f in glob.iglob(dd + "/*.time"):
                outprefix = f.rsplit('.', 1)[0] + os.path.basename(d)
            for f in glob.iglob(dd + "/*.iohist"):
                ioprof = [[float(v) for v in line.strip().split()] for line in open(f)]
                drawio.plot_ioprof(ioprof, outprefix, terminaltype)
            for f in glob.iglob(dd + "/*.cpuhist"):
                cpuprof = [[float(v) for v in line.strip().split()] for line in open(f)]
                output = f.rsplit('.', 1)[0] + os.path.basename(d) + "." + terminaltype
                drawcpu.plot_cpuprof(cpuprof, output, terminaltype)
            for f in glob.iglob(dd + "/*.cachehist"):
                cacheprof = [[float(v) for v in line.strip().split()] for line in open(f)]
                output = f.rsplit('.', 1)[0] + os.path.basename(d) + "cache." + terminaltype
                drawcachemiss.plot_cachemiss(cacheprof, output, terminaltype)
            for f in glob.iglob(dd + "/trace_*.iocosthist"):
                iocostprof = [[float(v) for v in line.strip().split()] for line in open(f)]
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

class workmem_plotter(object):
    def __init__(self, dbpath, terminaltype = "png"):
        self.conn = sqlite3.connect(dbpath)
        self.terminaltype = terminaltype
        self.plotprefdict = {}

    def init_gnuplot(self):
        gp = gpinit(self.terminaltype)
        #gp('set terminal epslatex color 11')
        gp.xlabel("working memory [byte]")
        gp('set format x "%.0b%B"')
        if xlogplot: gp('set logscale x 2')
        gp('set grid')
        if slide:
            if "eps" == terminaltype:
                gp('set termoption font "Times-Roman,28"')
                self.plotprefdict = {"with_" : "linespoints lt 1 lw 6" }
            elif "png" == terminaltype:
                gp('set termoption font "Times-Roman,18"')
                self.plotprefdict = {"with_" : "linespoints lw 2"}
        else:
            self.plotprefdict = {"with_" : "linespoints" }
        return gp

    def __del__(self):
        self.conn.close()

    def plot_workmem_exectime(self, output):
        gp = self.init_gnuplot()
        gp('set output "{0}"'.format(output))
        gp.ylabel("Time [s]")
        gp('set yrange [0:*]')
        gp('set key right top')
        nrow = self.conn.execute("select count(*) from iotrace").fetchone()[0]
        gds = []
        query = ("select workmem, avg(exectime) from measurement "
                 "group by workmem order by workmem")
        gds.extend(query2gds(self.conn, query, title = "Execution time", **self.plotprefdict))
        if nrow:
            query = ("select workmem, avg({y})/1000000000 from measurement, iotrace "
                     "where measurement.id = iotrace.id "
                     "group by workmem order by workmem")
            gds.extend(query2gds(self.conn, query.format(y = "readio_nsec"),
                                  title = "Read I/O cost", **self.plotprefdict))
            gds.extend(query2gds(self.conn, query.format(y = "writeio_nsec"),
                                  title = "Write I/O cost", **self.plotprefdict))
            gds.extend(query2gds(self.conn, query.format(y = "readio_nsec + writeio_nsec"),
                                  title = "I/O cost", **self.plotprefdict))
            query = ("select workmem, avg(exectime - (readio_nsec + writeio_nsec) / 1000000000) "
                     "from measurement, iotrace where measurement.id = iotrace.id "
                     "group by workmem order by workmem")
            gds.extend(query2gds(self.conn, query, title = "CPU cost", **self.plotprefdict))
        gp.plot(*gds)
        sys.stdout.write("output {0}\n".format(output))
        gp.close()

    def plot_workmem_io(self, output):
        gp = self.init_gnuplot()
        nrow = self.conn.execute("select count(*) from io").fetchone()[0]
        if not nrow: return
        gp('set output "{0}"'.format(output))
        gp.ylabel("Total I/O size [MB]")
        gp('set yrange [0:*]')
        gp('set key right center')
        query = ("select workmem, avg({y}) from measurement, io "
                 "where measurement.id = io.id "
                 "group by workmem order by workmem")
        gdr = query2gds(self.conn, query.format(y = "total_readmb"),
                         title = "Read", **self.plotprefdict)[0]
        gdw = query2gds(self.conn, query.format(y = "total_writemb"),
                         title = "Write", **self.plotprefdict)[0]
        gp.plot(gdr, gdw)
        sys.stdout.write("output {0}\n".format(output))
        gp.close()

    def plot_workmem_iocount(self, output):
        gp = self.init_gnuplot()
        nrow = self.conn.execute("select count(*) from iotrace").fetchone()[0]
        if not nrow: return
        gp('set output "{0}"'.format(output))
        gp.ylabel("I/O count")
        gp('set yrange[0:*]')
        gp('set key right center')
        query = ("select workmem, avg({y}) from measurement, iotrace "
                 "where measurement.id = iotrace.id "
                 "group by workmem order by workmem")
        gdr = query2gds(self.conn, query.format(y = "readio_count"),
                        title = "Read", **self.plotprefdict)[0]
        gdw = query2gds(self.conn, query.format(y = "writeio_count"),
                        title = "Write", **self.plotprefdict)[0]
        gp.plot(gdr, gdw)
        sys.stdout.write("output {0}\n".format(output))
        gp.close()

    def plot_workmem_cpuutil(self, output):
        gp = self.init_gnuplot()
        nrow = self.conn.execute("select count(*) from cpu").fetchone()[0]
        if not nrow: return
        gp('set output "{0}"'.format(output))
        gp.ylabel("CPU util [%]")
        gp('set yrange [0:100]')
        gp('set key outside top')
        gp('set style fill pattern 1 border')
        self.conn.row_factory = sqlite3.Row
        query = ("select workmem, avg(usr) as usr, avg(sys) as sys, avg(iowait) as iowait, "
                 "avg(irq) as irq, avg(soft) as soft, avg(idle) as idle "
                 "from measurement, cpu "
                 "where measurement.id = cpu.id "
                 "group by workmem order by workmem")
        cur = self.conn.cursor()
        cur.execute(query)
        r = cur.fetchone()
        keys = r.keys()
        xlist = []
        piledatas = [[] for i in range(len(keys[1:]))]
        xlist.append(r[0])
        piledatas[0].append(r[1])
        for i in range(2, len(keys)): piledatas[i - 1].append(piledatas[i - 2][-1] + r[i])
        for r in cur:
            xlist.append(r[0])
            piledatas[0].append(r[1])
            for i in range(2, len(keys)): piledatas[i - 1].append(piledatas[i - 2][-1] + r[i])
        gds = []
        widthlist = [v / 4 for v in xlist] if xlogplot else [2 ** 20 / 2 for v in xlist]
        for k, dat in zip(keys[:0:-1], piledatas[::-1]):
            gds.append(Gnuplot.Data(xlist, dat, widthlist,
                                    title = k,
                                    with_ = 'boxes fs solid border lc rgb "black"'))
        gp.plot(*gds)
        sys.stdout.write("output {0}\n".format(output))
        gp.close()

    def plot_workmem_cputime(self, output):
        gp = self.init_gnuplot()
        nrow = self.conn.execute("select count(*) from cpu").fetchone()[0]
        if not nrow: return
        gp('set output "{0}"'.format(output))
        gp('set ylabel "Time [s]" offset 2')
        gp('set yrange [0:*]')
        gp('set key inside top right')
        gp('set style fill pattern 1 border')
        self.conn.row_factory = sqlite3.Row
        query = ("select workmem, avg(exectime) as exectime, "
                 "avg(usr) / 100 as usr, avg(sys) / 100 as sys, "
                 "avg(iowait) / 100 as iowait, "
                 #"avg(irq) / 100 as irq, avg(soft) / 100 as soft, "
                 "avg(idle) / 100 as idle "
                 "from measurement, cpu "
                 "where measurement.id = cpu.id "
                 "group by workmem order by workmem")
        cur = self.conn.cursor()
        cur.execute(query)
        r = cur.fetchone()
        keys = r.keys()
        xlist = []
        piledatas = [[] for i in range(len(keys[2:]))]
        xlist.append(r[0])
        piledatas[0].append(r[2])
        for i in range(3, len(keys)): piledatas[i - 2].append(piledatas[i - 3][-1] + r[i])
        for i in range(len(keys[2:])): piledatas[i][-1] *= r[1]
        for r in cur:
            xlist.append(r[0])
            piledatas[0].append(r[2])
            for i in range(3, len(keys)): piledatas[i - 2].append(piledatas[i - 3][-1] + r[i])
            for i in range(len(keys[2:])): piledatas[i][-1] *= r[1]
        gds = []
        widthlist = [v / 4 for v in xlist] if xlogplot else [2 ** 20 / 2 for v in xlist]
        gp('set xrange [{0}:*]'.format(xlist[0] - widthlist[0] / 2))
        for k, dat in zip(keys[:0:-1], piledatas[::-1]):
            gds.append(Gnuplot.Data(xlist, dat, widthlist,
                                    title = k,
                                    with_ = 'boxes fs solid border lc rgb "black"'))
        # cache size line
        # gds.append(Gnuplot.Data([24 * 2 ** 20] * 2, [0, 1400], with_ = 'lines lw 2 lc 8'))
        gp.plot(*gds)
        sys.stdout.write("output {0}\n".format(output))
        gp.close()

    def plot_workmem_cache(self, output):
        gp = self.init_gnuplot()
        nrow = self.conn.execute("select count(*) from cache").fetchone()[0]
        if not nrow: return
        gp('set output "{0}"'.format(output))
        gp('set ytics nomirror')
        gp('set ylabel"count" offset 3')
        gp('set y2label "cache miss rate [%]" offset -2')
        gp('set grid xtics noytics noy2tics')
        gp('set yrange[0:*]')
        gp('set y2range [0:100]')
        gp('set y2tic 10')
        gp('set key inside right bottom')
        gds = []
        query = "select distinct workmem from measurement order by workmem"
        workmemlist = [r[0] for r in self.conn.execute(query)]
        datalist = [[[] for v in workmemlist] for i in range(3)]
        query = ("select workmem, cache_references, cache_misses "
                 "from measurement, cache "
                 "where measurement.id = cache.id "
                 "order by workmem")
        for r in self.conn.execute(query):
            idx = workmemlist.index(r[0])
            datalist[0][idx].append(r[1])
            datalist[1][idx].append(r[2])
            datalist[2][idx].append(float(r[2]) / r[1] * 100)
        if slide: plotprefdict = {"with_" : "yerrorlines lw 2"}
        else: plotprefdict = {"with_" : "yerrorlines"}
        for i, title in enumerate(("cache-references", "cache-misses")):
            gds.append(Gnuplot.Data(workmemlist,
                                    [np.mean(vals) for vals in datalist[i]],
                                    [np.std(vals) for vals in datalist[i]],
                                    title = title,
                                    axes = "x1y1", **plotprefdict))
        gds.append(Gnuplot.Data(workmemlist,
                                [np.mean(vals) for vals in datalist[2]],
                                [np.std(vals) for vals in datalist[2]],
                                title = "cache-miss-rates",
                                axes = "x1y2", **plotprefdict))

        # cache size line
        # gds.append(Gnuplot.Data([24 * 2 ** 20] * 2, [0, 100],
        #                         axes = "x1y2", with_ = 'lines lw 2 lc 8'))
        gp.plot(*gds)
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
    #gen_allgraph(rootdir, reliddict, terminaltype)

    xlogplot = True
    wp = workmem_plotter(rootdir + "/spec.db", terminaltype)

    output = "{0}/exectime.{1}".format(rootdir, terminaltype)
    wp.plot_workmem_exectime(output)

    output = "{0}/io.{1}".format(rootdir, terminaltype)
    wp.plot_workmem_io(output)

    output = "{0}/iocount.{1}".format(rootdir, terminaltype)
    wp.plot_workmem_iocount(output)

    output = "{0}/cpuutil.{1}".format(rootdir, terminaltype)
    wp.plot_workmem_cpuutil(output)

    output = "{0}/cputime.{1}".format(rootdir, terminaltype)
    wp.plot_workmem_cputime(output)

    output = "{0}/cache.{1}".format(rootdir, terminaltype)
    wp.plot_workmem_cache(output)
