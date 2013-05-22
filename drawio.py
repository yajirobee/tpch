#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil

class ioprofiler(object):
    def __init__(self, devname):
        self.devname = devname
        if devname == "md0":
            self.get_ioprof = self.get_mdioprof
        else:
            self.get_ioprof = self.get_normioprof

    def get_mdioprof(self, fpath):
        rmbps, wmbps, riops, wiops, ioutil = [], [], [], [], []
        tmp = []
        comppat = re.compile(r'fio[a-h]')
        for line in open(fpath):
            val = line.split()
            if not val:
                if tmp:
                    ioutil.append(sum(tmp) / len(tmp))
                    tmp = []
            elif val[0] == self.devname:
                riops.append(float(val[3]))
                wiops.append(float(val[4]))
                rmbps.append(float(val[5]) * 512 * (10 ** -6)) # 5th column is rsec/s
                wmbps.append(float(val[6]) * 512 * (10 ** -6)) # 6th column is wsec/s
            elif comppat.match(val[0]):
                tmp.append(float(val[11]))
        return rmbps, wmbps, riops, wiops, ioutil

    def get_normioprof(self, fpath):
        rmbps, wmbps, riops, wiops, ioutil = [], [], [], [], []
        for line in open(fpath):
            val = line.split()
            if not val:
                continue
            elif val[0] == self.devname:
                riops.append(float(val[3]))
                wiops.append(float(val[4]))
                rmbps.append(float(val[5]) * 512 * (10 ** -6)) # 5th column is rsec/s
                wmbps.append(float(val[6]) * 512 * (10 ** -6)) # 6th column is wsec/s
                ioutil.append(float(val[11]))
        return rmbps, wmbps, riops, wiops, ioutil

def plot_ioprof(ioprof, outprefix, terminaltype = "png"):
    rmbps, wmbps, riops, wiops, ioutil = ioprof
    gp = plotutil.gpinit(terminaltype)
    gp.xlabel("elapsed time [s]")
    gp('set grid')
    gp('set termoption font "Times-Roman,22"')

    # draw mbps graph
    output = "{0}mbps.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("MBps")
    gp.ylabel("I/O throughput [MB/s]")
    gdrmbps = Gnuplot.Data(range(len(rmbps)), rmbps,
                           with_ = "lines lw 2", title = "read")
                           #with_ = "lines", title = "read MBps")
    gdwmbps = Gnuplot.Data(range(len(wmbps)), wmbps,
                           with_ = "lines lw 2 lc 3", title = "write")
                           #with_ = "lines", title = "write MBps")
    gp.plot(gdrmbps, gdwmbps)
    sys.stdout.write("output {0}\n".format(output))

    # draw iops graph
    output = "{0}iops.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("I/O throughput [IO/s]")
    gdriops = Gnuplot.Data(range(len(riops)), riops,
                           with_ = "lines", title = "read")
    gdwiops = Gnuplot.Data(range(len(wiops)), wiops,
                           with_ = "lines", title = "write")
    gp.plot(gdriops, gdwiops)
    sys.stdout.write("output {0}\n".format(output))

    # draw iosize graph
    output = "{0}iosize.{1}".format(outprefix, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.ylabel("iosize [KB]")
    rios = [(rmb * 1000.) / rio if rio != 0 else 0.
            for rmb, rio in zip(rmbps, riops)]
    wios = [(wmb * 1000) / wio if wio != 0 else 0.
            for wmb, wio in zip(wmbps, wiops)]
    gdrios = Gnuplot.Data(range(len(rios)), rios,
                          with_ = "lines", title = "read iosize")
    gdwios = Gnuplot.Data(range(len(wios)), wios,
                          with_ = "lines", title = "write iosize")
    gp.plot(gdrios, gdwios)
    sys.stdout.write("output {0}\n".format(output))

    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        iofile = sys.argv[1]
        devname = sys.argv[2]
        terminaltype = "png"
    elif len(sys.argv) == 4:
        iofile = sys.argv[1]
        devname = sys.argv[2]
        terminaltype = sys.argv[3]
    else:
        sys.stdout.write(
            "Usage : {0} iostatfile devname [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    ioprofiler = ioprofiler(devname)
    ioprof = ioprofiler.get_ioprof(iofile)
    outprefix = iofile.rsplit('.', 1)[0]

    plot_ioprof(ioprof, outprefix, terminaltype)
