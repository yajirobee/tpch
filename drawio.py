#! /usr/bin/env python

import sys, os, re, Gnuplot
import plotutil

terminaltype = "png"
if terminaltype != "png" and terminaltype != "eps":
    sys.stdout.write("wrong terminal type\n")
    sys.exit(1)

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
                iops.append(float(val[11]))
        return rmbps, wmbps, riops, wiops, ioutil

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stdout.write("Usage : {0} ioproffile devname\n".format(sys.argv[0]))
        sys.exit(0)

    iofile = sys.argv[1]
    devname = sys.argv[2]
    ioprof = ioprofiler(devname)
    rmbps, wmbps, riops, wiops, ioutil = ioprof.get_ioprof(iofile)
    fprefix = iofile.rsplit('.', 1)[0]

    # draw mbps graph
    gp = plotutil.gpinit(terminaltype)
    fpath = "{0}mbps.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("MBps")
    gp('set grid')
    gdrmbps = Gnuplot.Data(range(len(rmbps)), rmbps,
                           with_ = "lines", title = "read MBps")
    gdwmbps = Gnuplot.Data(range(len(wmbps)), wmbps,
                           with_ = "lines", title = "write MBps")
    gp.plot(gdrmbps, gdwmbps)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()

    # draw iops graph
    gp = plotutil.gpinit(terminaltype)
    fpath = "{0}iops.{1}".format(fprefix, terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time(s)")
    gp.ylabel("iops")
    gp('set grid')
    gdriops = Gnuplot.Data(range(len(riops)), riops,
                           with_ = "lines", title = "read iops")
    gdwiops = Gnuplot.Data(range(len(wiops)), wiops,
                           with_ = "lines", title = "write iops")
    gp.plot(gdriops, gdwiops)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()
