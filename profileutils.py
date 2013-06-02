#! /usr/bin/env python

import sys, os, re

def get_mdioprof(fpath, devname):
    rmbps, wmbps, riops, wiops, ioutil = [], [], [], [], []
    tmp = []
    comppat = re.compile(r'fio[a-h]')
    for line in open(fpath):
        val = line.split()
        if not val:
            if tmp:
                ioutil.append(sum(tmp) / len(tmp))
                tmp = []
        elif val[0] == devname:
            riops.append(float(val[3]))
            wiops.append(float(val[4]))
            rmbps.append(float(val[5]) * 512 * (10 ** -6)) # 5th column is rsec/s
            wmbps.append(float(val[6]) * 512 * (10 ** -6)) # 6th column is wsec/s
        elif comppat.match(val[0]):
            tmp.append(float(val[11]))
    return rmbps, wmbps, riops, wiops, ioutil

def get_normioprof(fpath, devname):
    rmbps, wmbps, riops, wiops, ioutil = [], [], [], [], []
    for line in open(fpath):
        val = line.split()
        if not val:
            continue
        elif val[0] == devname:
            riops.append(float(val[3]))
            wiops.append(float(val[4]))
            rmbps.append(float(val[5]) * 512 * (10 ** -6)) # 5th column is rsec/s
            wmbps.append(float(val[6]) * 512 * (10 ** -6)) # 6th column is wsec/s
            ioutil.append(float(val[11]))
    return rmbps, wmbps, riops, wiops, ioutil

def get_ioprof(fpath, devname):
    "get histgram of IO profile"
    if devname == "md0":
        return get_mdioprof(fpath, devname)
    else:
        return get_normioprof(fpath, devname)

def get_cpuprof(fpath, core):
    "get histgram of a CPU core usage"
    coreutil = []
    for line in open(fpath):
        val = line.split()
        if not val:
            continue
        elif val[1] == core:
            coreutil.append([float(v) for v in val[2:]])
    return coreutil

def get_allcpuprof(fpath, col):
    "get histgram of one column of all CPU cores usage"
    datepat = re.compile(r"\d{2}:\d{2}:\d{2}")
    floatpat = re.compile(r"\d+(?:\.\d*)?|\.\d+")
    utilhist = []
    util = 0.
    date = None
    for line in open(fpath):
        val = line.split()
        if not val or val[1] == "all" or val[1] == "CPU":
            continue
        elif date != val[0] and datepat.search(val[0]):
            if date:
                utilhist.append(util)
            date = val[0]
            util = 0.
        if floatpat.search(val[col]):
            tmp = float(val[col])
            if tmp > 2.0:
                util += tmp
    return utilhist

def get_reliddict(relidfile):
    "get relid dictionary"
    reliddict = {}
    for line in open(relidfile):
        vals = [v.strip() for v in line.split('|')]
        if len(vals) != 2 or not vals[0].isdigit():
            continue
        else:
            reliddict[int(vals[0])] = vals[1]
    return reliddict

def get_tblrefprof(iodumpfile):
    "get histgram of each table reference counts"
    refhist = []
    with open(iodumpfile) as fo:
        line = fo.readline()
        vals = line.split()
        stime = int(vals[0], 16)
        elapsed = 0
        refdict = {int(vals[5], 16) : 1}
        for line in fo:
            vals = line.split()
            time = (int(vals[0], 16) - stime) / 1000 ** 3
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

def get_iocostprof(fpath):
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
