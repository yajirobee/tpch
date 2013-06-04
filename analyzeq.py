#! /usr/bin/env python

import sys, os, glob, re, Gnuplot, sqlite3
import drawio, drawcpu, drawiocost, drawioref
from profileutils import get_reliddict
from plotutil import query2data, gpinit

slide = False

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
    conn = sqlite3.connect(dbpath)
    tbls = [r[0] for r
            in conn.execute("select name from sqlite_master where type = 'table'")]
    gds = []
    query = ("select workmem, avg(exectime) from measurement "
             "group by workmem order by workmem")
    gds.extend(query2data(conn, query, title = "Execution time", **plotprefdict))
    if "iotrace" in tbls:
        query = ("select workmem, avg({y})/1000000000 from measurement, iotrace "
                 "where measurement.id = iotrace.id "
                 "group by workmem order by workmem")
        gds.extend(query2data(conn, query.format(y = "readio_nsec"),
                              title = "Read I/O cost", **plotprefdict))
        gds.extend(query2data(conn, query.format(y = "writeio_nsec"),
                              title = "Write I/O cost", **plotprefdict))
        gds.extend(query2data(conn, query.format(y = "readio_nsec + writeio_nsec"),
                              title = "I/O cost", **plotprefdict))
        query = ("select workmem, avg(exectime - (readio_nsec + writeio_nsec) / 1000000000) "
                 "from measurement, iotrace where measurement.id = iotrace.id "
                 "group by workmem order by workmem")
        gds.extend(query2data(conn, query, title = "CPU cost", **plotprefdict))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

def plot_workmem_io(dbpath, output, terminaltype = "png"):
    conn = sqlite3.connect(dbpath)
    tbls = [r[0] for r
            in conn.execute("select name from sqlite_master where type = 'table'")]
    if "io" not in tbls:
        return
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
            gp('set termoption font "Times-Roman,18"')
            plotprefdict = {"with_" : "linespoints lw 2"}
    else:
        plotprefdict = {"with_" : "linespoints" }
    query = ("select workmem, avg({y}) from measurement, io "
             "where measurement.id = io.id "
             "group by workmem order by workmem")
    gdr = query2data(conn, query.format(y = "total_readmb"),
                     title = "Read", **plotprefdict)[0]
    gdw = query2data(conn, query.format(y = "total_writemb"),
                     title = "Write", **plotprefdict)[0]
    gp.plot(gdr, gdw)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

def plot_workmem_iocount(dbpath, output, terminaltype):
    conn = sqlite3.connect(dbpath)
    tbls = [r[0] for r
            in conn.execute("select name from sqlite_master where type = 'table'")]
    if "iotrace" not in tbls:
        return
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
    query = ("select workmem, avg({y}) from measurement, iotrace "
             "where measurement.id = iotrace.id "
             "group by workmem order by workmem")
    gdr = query2data(dbpath, query.format(y = "readio_count"),
                     title = "Read", **plotprefdict)[0]
    gdw = query2data(dbpath, query.format(y = "writeio_count"),
                     title = "Write", **plotprefdict)[0]
    gp.plot(gdr, gdw)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()

def plot_workmem_cpuutil(dbpath, output, terminaltype):
    conn = sqlite3.connect(dbpath)
    tbls = [r[0] for r
            in conn.execute("select name from sqlite_master where type = 'table'")]
    if "cpu" not in tbls:
        return
    gp = gpinit(terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("working memory")
    gp.ylabel("CPU util [%]")
    gp('set grid')
    gp('set logscale x')
    gp('set format x "%.0s%cB"')
    gp('set xrange [10000:*]')
    gp('set yrange [0:100]')
    gp('set key outside')
    gp('set style fill pattern 1 border')
    conn = sqlite3.connect(dbpath)
    conn.row_factory = sqlite3.Row
    query = ("select workmem, avg(usr) as usr, avg(sys) as sys, avg(iowait) as iowait, "
             "avg(irq) as irq, avg(soft) as soft, avg(idle) as idle "
             "from measurement, cpu "
             "where measurement.id = cpu.id "
             "group by workmem order by workmem")
    cur = conn.cursor()
    cur.execute(query)
    r = cur.fetchone()
    keys = r.keys()
    xlist = []
    piledatas = [[] for i in range(len(keys[1:]))]
    xlist.append(r[0])
    piledatas[0].append(r[1])
    for i in range(2, len(keys)):
        piledatas[i - 1].append(piledatas[i - 2][-1] + r[i])
    for r in cur:
        xlist.append(r[0])
        piledatas[0].append(r[1])
        for i in range(2, len(keys)):
            piledatas[i - 1].append(piledatas[i - 2][-1] + r[i])
    gds = []
    for k, dat in zip(keys[:0:-1], piledatas[::-1]):
        gds.append(Gnuplot.Data(xlist, dat, [v / 4 for v in xlist], title = k,
                               with_ = 'boxes fs solid border lc rgb "black"'))
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
    output = "{0}/exectime.{1}".format(rootdir, terminaltype)
    plot_workmem_exectime(rootdir + "/spec.db", output, terminaltype)
    output = "{0}/io.{1}".format(rootdir, terminaltype)
    plot_workmem_io(rootdir + "/spec.db", output, terminaltype)
    output = "{0}/iocount.{1}".format(rootdir, terminaltype)
    plot_workmem_iocount(rootdir + "/spec.db", output, terminaltype)
    output = "{0}/cpuutil.{1}".format(rootdir, terminaltype)
    plot_workmem_cpuutil(rootdir + "/spec.db", output, terminaltype)
