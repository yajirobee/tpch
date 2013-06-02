#! /usr/bin/env python

import sys, os, Gnuplot
import plotutil

def get_iocosthist(fpath):
    readiohist = [0]
    writeiohist = [0]
    interval = 10 ** 9
    prevstate = None
    for i, line in enumerate(open(fpath)):
        val = line.strip().split()
        if not val:
            continue
        if 'r' == val[1]:
            if 'r' == prevstate:
                sys.stderr.write("bat IO sequence : line {0}\n".format(i))
                sys.exit(1)
            stime = int(val[0], 16)
            for i in range(stime / interval - (len(readiohist) - 1)):
                readiohist.append(0)
        elif 'R' == val[1]:
            if ('r' != prevstate) or (int(val[3], 16) != prevblock):
                sys.stderr.write("bat IO sequence : line {0}\n".format(i))
                sys.exit(1)
            ftime = int(val[0], 16)
            while stime / interval < ftime / interval:
                readiohist[-1] += len(readiohist) * interval - stime
                stime = len(readiohist) * interval
                readiohist.append(0)
            readiohist[-1] += ftime - stime
        elif 'w' == val[1]:
            if 'w' == prevstate:
                sys.stderr.write("bat IO sequence : line {0}\n".format(i))
                sys.exit(1)
            stime = int(val[0], 16)
            for i in range(stime / interval - (len(writeiohist) - 1)):
                writeiohist.append(0)
        elif 'W' == val[1]:
            if ('w' != prevstate) or (int(val[3], 16) != prevblock):
                sys.stderr.write("bat IO sequence : line {0}\n".format(i))
                sys.exit(1)
            ftime = int(val[0], 16)
            while stime / interval < ftime / interval:
                writeiohist[-1] += len(writeiohist) * interval - stime
                stime = len(writeiohist) * interval
                writeiohist.append(0)
            writeiohist[-1] += ftime - stime
        prevstate = val[1]
        prevblock = int(val[3], 16)
    return readiohist, writeiohist

def main(iotracefile, terminaltype):
    interval = 10. ** 9
    iohists = get_iocosthist(iotracefile)
    sys.stdout.write(
        ("total read I/O time : {0} [sec]\n"
         "total write I/O time : {1} [sec]\n"
         .format(sum(iohists[0]) / interval,
                 sum(iohists[1]) / interval)))
    fprefix = iotracefile.rsplit('.', 1)[0]
    fpath = "{0}iocosthist.{1}".format(fprefix, terminaltype)
    gp = plotutil.gpinit(terminaltype)
    gp('set output "{0}"'.format(fpath))
    gp.xlabel("elapsed time [s]")
    gp.ylabel("I/O ratio [%]")
    gp('set grid front')
    gds = []
    gds.append(Gnuplot.Data(range(len(iohists[0])),
                            [v / interval for v in iohists[0]],
                            with_ = "lines",
                            title = "Read"))
    gds.append(Gnuplot.Data(range(len(iohists[1])),
                            [v / interval for v in iohists[1]],
                            with_ = "lines",
                            title = "Write"))
    gp.plot(*gds)
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
        sys.stdout.write("Usage : {0} iotracefile [png|eps]\n".format(sys.argv[0]))
        sys.exit(0)

    main(iotracefile, terminaltype)
