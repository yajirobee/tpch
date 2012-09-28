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
            throughput.append(float(val[5]) * 0.001)
        elif devpat.match(val[0]):
            tmp.append(float(val[11]))
    return (throughput, iops, ioutil)

def ceiltop(val):
    tmp = float(val)
    count = 0
    if tmp == 0.0:
        return tmp
    elif tmp >= 1.0:
        while tmp >= 1.0:
            tmp *= 0.1
            count += 1
        tmp *= 10
        count -= 1
    else:
        while tmp < 1.0:
            tmp *= 10
            count -= 1
    if tmp - int(tmp) == 0.0:
        return int(tmp) * (10 ** count)
    else:
        return (int(tmp) + 1) * (10 ** count)

def floortop(val):
    tmp = float(val)
    count = 0
    if tmp == 0.0:
        return tmp
    elif val >= 1.0:
        while tmp >= 1.0:
            tmp *= 0.1
            count += 1
        tmp *= 10
        count -= 1
    else:
        while tmp < 1.0:
            tmp *= 10
            count -= 1
    return int(tmp) * (10 ** count)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stdout.write("Usage : {0} cpuproffile ioproffile\n".format(sys.argv[0]))
        sys.exit(0)

    sysutil = get_cpuprof(sys.argv[1])
    throughput, iops, ioutil = get_ioprof(sys.argv[2])

    fprefix = sys.argv[1].rsplit('.', 1)[0]
    gp = Gnuplot.Gnuplot()
    gp(settermcmd)
    fpath = "{0}thio.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("read throughput(MB/s)")
    gp('set y2label "read iops"')
    gp('set ytics nomirror')
    maxiopsrng = ceiltop(max(iops))
    miniopsrng = floortop(min(iops))
    gp('set y2range [{0}:{1}]'.format(miniopsrng, maxiopsrng))
    gp('set y2tics {0}'.format((maxiopsrng - miniopsrng) / 10))
    gdthpt = Gnuplot.Data(range(len(throughput)), throughput,
                          with_ = "lines", title = "throughput", axes = "x1y1")
    gdiops = Gnuplot.Data(range(len(iops)), iops,
                          with_ = "lines", title = "iops", axes = "x1y2")
    gp.plot(gdthpt, gdiops)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()

    gp = Gnuplot.Gnuplot()
    gp(settermcmd)
    fpath = "{0}util.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("util(%)")
    gdcpu = Gnuplot.Data(range(len(sysutil)), sysutil,
                         with_ = "lines", title = "cpuutil")
    gdio = Gnuplot.Data(range(len(ioutil)), ioutil,
                        with_ = "lines", title = "ioutil")
    gp.plot(gdcpu, gdio)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()
