#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil

def getoiddict(oidfile):
    oiddict = {}
    for line in open(oidfile):
        vals = [v.strip() for v in line.split('|')]
        if len(vals) != 2 or not vals[0].isdigit():
            continue
        else:
            oiddict[int(vals[0])] = vals[1]
    return oiddict

def getrefhist(iodumpfile):
    refhist = []
    with open(iodumpfile) as fo:
        line = fo.readline()
        vals = line.split()
        stime = int(vals[0], 16)
        elapsed = 0
        refdict = {int(vals[5], 16) : 1}
        for line in fo:
            vals = line.split()
            time = (int(vals[0], 16) - stime) / 10000 ** 2
            if time == elapsed:
                relname = int(vals[5], 16)
                if relname in refdict:
                    refdict[relname] += 1
                else:
                    refdict[relname] = 1
            else:
                assert(time > elapsed)
                for i in range(time - elapsed):
                    refhist.append(refdict)
                    refdict = {}
                refdict[int(vals[5], 16)] = 1
                elapsed = time
    return refhist


if __name__ == "__main__":
    if len(sys.argv) == 3:
        iodumpfile = sys.argv[1]
        oidfile = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        iodumpfile = sys.argv[1]
        oidfile = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stdout.write(
            "Usage : {0} iodumpfile oidfile [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    oiddict = getoiddict(oidfile)
    refhist = getrefhist(iodumpfile)
    rellist = []
    for d in refhist:
        for k in d:
            if k not in rellist and k > 15000:
                rellist.append(k)

    fprefix = iodumpfile.rsplit('.', 1)[0]
    gp = plotutil.gpinit(terminaltype)
    fpath = "{0}refhist.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("count(pages)")
    #gp('set key outside')
    gp('set grid front')
    gp('set style fill pattern 1 border')
    gd = []
    xlen = len(refhist)
    piledatas = [[] for i in range(len(rellist))]
    for d in refhist:
        for i, oid in enumerate(rellist):
            if i == 0:
                piledatas[i].append(d.get(oid, 0))
            else:
                piledatas[i].append(piledatas[i - 1][-1] + d.get(oid, 0))
    gd = []
    for i, oid in enumerate(rellist):
        if i == 0:
            gd.append(Gnuplot.Data(range(xlen), piledatas[i],
                                   with_ = "filledcurve x1", title = oiddict[oid]))
        else:
            gd.append(Gnuplot.Data(range(xlen), piledatas[i], piledatas[i - 1],
                                   with_ = "filledcurve", title = oiddict[oid]))
    gp.plot(*gd)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()
