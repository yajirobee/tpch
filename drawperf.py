#! /usr/bin/env python

import sys, os, re, Gnuplot

terminaltype = "png"
if terminaltype == "eps":
    settermcmd = 'set terminal postscript eps color "Times-Roman,26"'
elif terminaltype == "png":
    settermcmd = "set terminal png"
else:
    sys.stdout.write("wrong terminal type\n")
    sys.exit(1)

def get_cpuprof(fpath):
    sysutil = []
    util = 0.
    date = None
    for line in open(fpath):
        val = line.split()
        if date == val[0]:
            util += float(val[2])
        else:
            if date:
                sysutil.append(util)
            date = val[0]
            util = float(val[2])
    return sysutil

def get_ioprof(fpath):
    throughput, iops, ioutil = [], [], []
    tmp = []
    devpat = re.compile(r'fio[a-h]')
    for line in open(fpath):
        val = line.split()
        if not val:
            if tmp:
                ioutil.append(sum(tmp) / len(tmp))
                tmp = []
        elif val[0] == "md0":
            iops.append(float(val[3]))
            throughput.append(float(val[5]))
        elif devpat.match(val[0]):
            tmp.append(float(val[11]))
    return (throughput, iops, ioutil)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stdout.write("Usage : {0} cpuproffile ioproffile\n".format(sys.argv[0]))
        sys.exit(0)

    sysutil = get_cpuprof(sys.argv[1])
    throughput, iops, ioutil = get_ioprof(sys.argv[2])

    fprefix = sys.argv[1].rsplit('.', 1)[0]
    gp = Gnuplot.Gnuplot()
    gp(settermcmd)
    gp('set output "{0}"'.format("{0}thio.{1}".format(fprefix, terminaltype)))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("read throughput(B)")
    gp('set y2label "read iops"')
    gp('set ytics nomirror')
    gp('set y2tics {0}'.format((max(iops) - min(iops)) / 10))
    gp('set y2range [{0}:{1}]'.format(min(iops) * 1.01, max(iops) * 1.01))
    gdthpt = Gnuplot.Data(range(len(throughput)), throughput,
                          with_ = "lines", title = "throughput", axes = "x1y1")
    gdiops = Gnuplot.Data(range(len(iops)), iops,
                          with_ = "lines", title = "iops", axes = "x1y2")
    gp.plot(gdthpt, gdiops)
    gp.close()

    gp = Gnuplot.Gnuplot()
    gp(settermcmd)
    gp('set output "{0}"'.format("{0}util.{1}".format(fprefix, terminaltype)))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("util(%)")
    gdcpu = Gnuplot.Data(range(len(sysutil)), sysutil,
                         with_ = "lines", title = "cpuutil")
    gdio = Gnuplot.Data(range(len(ioutil)), ioutil,
                        with_ = "lines", title = "ioutil")
    gp.plot(gdcpu, gdio)
    gp.close()
