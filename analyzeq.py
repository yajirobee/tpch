#! /usr/bin/env python

import sys, os, glob, re, Gnuplot, sqlite3
import drawiocost, drawioref
import numpy as np
from dbprofutils import get_reliddict
from plotutil import query2data, query2gds, gpinit, ceiltop

import drawio, drawcpu, drawcache, generategraphsdir

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
    statfiles = generategraphsdir.search_statfiles(rootdir)
    generategraphsdir.generate_allstatgraphs(statfiles, terminaltype = terminaltype)
    for d in glob.iglob(rootdir + "/workmem*"):
        for dd in glob.iglob(d + "/[0-9]*"):
            outprefix = dd + "/default"
            for f in glob.iglob(dd + "/*.res"):
                outprefix = os.path.splitext(f)[0] + os.path.basename(d)
            for f in glob.iglob(dd + "/*.time"):
                outprefix = os.path.splitext(f)[0] + os.path.basename(d)
            for f in glob.iglob(dd + "/trace_*.iocosthist"):
                iocostprof = [[float(v) for v in line.strip().split()] for line in open(f)]
                output = "{0}_iocosthist.{1}".format(outprefix, terminaltype)
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
                    output = "{0}_iorefhist.{1}".format(outprefix, terminaltype)
                    drawioref.plot_tblrefhist(reliddict, iorefhist, output, terminaltype)

class workmem_plotter(object):
    def __init__(self, dbpath, terminaltype = "png"):
        self.conn = sqlite3.connect(dbpath)
        self.terminaltype = terminaltype
        self.plotprefdict = {}

    def init_gnuplot(self):
        gp = gpinit(self.terminaltype)
        #gp('set terminal epslatex color 11')
        gp.xlabel("work\_mem [byte]")
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
        query = ("select workmem, avg({y} * exectime) from measurement, io "
                 "where measurement.id = io.id "
                 "group by workmem order by workmem")
        gdr = query2gds(self.conn, query.format(y = "average_readmb"),
                         title = "Read", **self.plotprefdict)[0]
        gdw = query2gds(self.conn, query.format(y = "average_writemb"),
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
        nrow = self.conn.execute("select count(*) from cpu").fetchone()[0]
        if not nrow: return
        gp = self.init_gnuplot()
        query = "select max(usr + sys + iowait + idle) from cpu"
        maxper = int(round(self.conn.execute(query).fetchone()[0], -2))
        gp('set output "{0}"'.format(output))
        gp.ylabel("CPU util [%]")
        gp('set yrange [0:{0}]'.format(maxper))
        gp('set key outside top')
        gp('set style fill pattern 1 border')
        query = ("select workmem, avg(usr) as usr, avg(sys) as sys, avg(iowait) as iowait, "
                 "avg(irq) as irq, avg(soft) as soft, avg(idle) as idle "
                 "from measurement, cpu "
                 "where measurement.id = cpu.id "
                 "group by workmem order by workmem")
        datas = query2data(self.conn, query)
        keys = ("workmem", "exectime", "usr", "iowait", "irq", "soft", "idle")
        xlist = datas[0]
        piledatas = [np.array(datas[1])]
        for d in datas[2:]: piledatas.append(np.array(d) + piledatas[-1])
        piledatas = [d.tolist() for d in piledatas]
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
        nrow = self.conn.execute("select count(*) from cpu").fetchone()[0]
        if not nrow: return
        gp = self.init_gnuplot()
        query = "select max(usr + sys + iowait + idle + irq + soft) from cpu"
        maxper = int(round(self.conn.execute(query).fetchone()[0], -2))
        gp('set output "{0}"'.format(output))
        gp('set ylabel "Time [s]" offset 2')
        gp('set yrange [0:*]')
        gp('set key inside top left')
        gp('set style fill pattern 1 border')
        query = ("select workmem, avg(exectime) as exectime, "
                 "avg(usr) / {maxper} as usr, avg(sys) / {maxper} as sys, "
                 "avg(iowait) / {maxper} as iowait, "
                 "avg(irq) / {maxper} as irq, avg(soft) / {maxper} as soft, "
                 "avg(idle) / {maxper} as idle "
                 "from measurement, cpu "
                 "where measurement.id = cpu.id "
                 "group by workmem order by workmem"
                 .format(maxper = maxper))
        datas = query2data(self.conn, query)
        keys = ("workmem", "exectime", "usr", "iowait", "irq", "soft", "idle")
        xlist = datas[0]
        exectimes = np.array(datas[1])
        piledatas = [np.array(datas[2])]
        for d in datas[3:]: piledatas.append(np.array(d) + piledatas[-1])
        for d in piledatas: d *= exectimes
        piledatas = [d.tolist() for d in piledatas]
        with open("{0}/cputime.dat".format(os.path.dirname(output)), "w") as fo:
            for vals in zip(xlist, *piledatas[::-1]):
                fo.write("{0}\n".format('\t'.join([str(v) for v in vals])))
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
        nrow = self.conn.execute("select count(*) from cache").fetchone()[0]
        if not nrow: return
        gp = self.init_gnuplot()
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
        y1axes = [{"name": "cache-references", "values": [[] for v in workmemlist]},
                  {"name": "cache-misses", "values": [[] for v in workmemlist]}]

        y2axes = [{"name": "cache-miss-rates", "values": [[] for v in workmemlist]}]
        query = ("select workmem, cache_references, cache_misses "
                 "from measurement, cache "
                 "where measurement.id = cache.id "
                 "order by workmem")
        # y1axes = [{"name": "all-cache-references", "values": [[] for v in workmemlist]},
        #           {"name": "L1D-cache-misses", "values": [[] for v in workmemlist]},
        #           {"name": "L2-cache-misses", "values": [[] for v in workmemlist]},
        #           {"name": "L3-cache-misses", "values": [[] for v in workmemlist]}]

        # y2axes = [{"name": "L1D-cache-miss-rates", "values": [[] for v in workmemlist]},
        #           {"name": "L2-cache-miss-rates", "values": [[] for v in workmemlist]},
        #           {"name": "L3-cache-miss-rates", "values": [[] for v in workmemlist]}]
        # query = ("select workmem, all_cache_references, L1D_cache_misses,L2_cache_misses,L3_cache_misses "
        #          "from measurement, cache "
        #          "where measurement.id = cache.id "
        #          "order by workmem")
        for r in self.conn.execute(query):
            idx = workmemlist.index(r[0])
            for i, axis in enumerate(y1axes): axis["values"][idx].append(r[i + 1])
            for i, axis in enumerate(y2axes):
                axis["values"][idx].append(float(r[i + 2]) / r[i + 1] * 100)
        if slide: plotprefdict = {"with_" : "yerrorlines lw 2"}
        else: plotprefdict = {"with_" : "yerrorlines"}
        for axis in y1axes:
            gds.append(Gnuplot.Data(workmemlist,
                                    [np.mean(vals) for vals in axis["values"]],
                                    [np.std(vals) for vals in axis["values"]],
                                    title = axis["name"], axes = "x1y1",
                                    **plotprefdict))
        for axis in y2axes:
            gds.append(Gnuplot.Data(workmemlist,
                                    [np.mean(vals) for vals in axis["values"]],
                                    [np.std(vals) for vals in axis["values"]],
                                    title = axis["name"], axes = "x1y2",
                                    **plotprefdict))

        # cache size line
        # gds.append(Gnuplot.Data([24 * 2 ** 20] * 2, [0, 100],
        #                         axes = "x1y2", with_ = 'lines lw 2 lc 8'))
        gp.plot(*gds)
        sys.stdout.write("output {0}\n".format(output))
        gp.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write(
            "Usage : {0} rootdir [relidfile] [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    rootdir = sys.argv[1]
    relidfile = sys.argv[2] if len(sys.argv) >= 3 else None
    terminaltype = sys.argv[3] if len(sys.argv) >= 4 else "png"
    if terminaltype != "png" and terminaltype != "eps":
        sys.stderr.write("wrong terminal type\n")
        sys.exit(1)

    reliddict = get_reliddict(relidfile) if relidfile else None
    gen_allgraph(rootdir, reliddict, terminaltype)

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
