#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil

def get_iocosthist(fpath):
    iocosthist = [0]
    interval = 10 ** 9
    time = 0
    prevstate = None
    for line in open(fpath):
        val = line.strip().split()
        if not val:
            continue
        elif 'S' == val[1]:
            if 'S' == prevstate:
                sys.stderr.write("bat IO sequence\n")
                sys.exit(1)
            stime = int(val[0], 16)
            prevstate = val[1]
            prevblock = int(val[3], 16)
            if stime / interval > time:
                time += 1
                iocosthist.append(0)
        elif 'F' == val[1]:
            if ('S' != prevstate) or (int(val[3], 16) != prevblock):
                sys.stderr.write("bat IO sequence\n")
                sys.exit(1)
            ftime = int(val[0], 16)
            prevstate = val[1]
            prevblock = int(val[3], 16)
            while stime / interval < ftime / interval:
                iocosthist[time] += (time + 1) * interval - stime
                time += 1
                stime = time * interval
                iocosthist.append(0)
            iocosthist[time] += ftime - stime
    return iocosthist

def main(iotracefile, terminaltype):
    iocosthist = get_iocosthist(iotracefile)
    sys.stdout.write("total I/O time : {0} [sec]\n".format(sum(iocosthist) / 10. ** 9))

    fprefix = iotracefile.rsplit('.', 1)[0]
    fpath = "{0}iocosthist.{1}".format(fprefix, terminaltype)
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("I/O ratio [%]")
    gp('set grid front')
    gd = Gnuplot.Data(range(len(iocosthist)), [v / 10. ** 9 for v in iocosthist],
                      with_ = "lines")
    gp.plot(gd)
    sys.stdout.write("output {0}\n".format(fpath))
    gp.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        iotracefile = sys.argv[1]
        terminaltype = "png"
    elif len(sys.argv) == 3:
        iotracefile = sys.argv[1]
        terminaltype = sys.argv[2]
    else:
        sys.stdout.write("Usage : {0} iotracefile\n".format(sys.argv[0]))
        sys.exit(0)

    main(iotracefile, terminaltype)
