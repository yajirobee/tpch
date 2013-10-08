#! /usr/bin/env python

import sys, os, re, glob
import numpy as np

def get_mdioprof(fpath, devname):
    ioprof = []
    comppat = re.compile(r'fio[a-h]')
    tmp = None
    comp = []
    for line in open(fpath):
        val = line.split()
        if not val:
            if tmp:
                if comp:
                    ave = comp[0]
                    for arr in comp[1:]: ave += arr
                    for i in range(6, ave.size): ave[i] /= len(comp)
                    tmp[:2] = ave[:2]
                    tmp[6:] = ave[6:]
                    comp = []
                tmp[4] *= 512 * (10 ** -6) # convert read throughput from sec/s to MB/s
                tmp[5] *= 512 * (10 ** -6) # convert write throughput from sec/s to MB/s
                ioprof.append(tmp)
                tmp = None
        elif val[0] == devname:
            tmp = [float(v) for v in val[1:]]
        elif comppat.match(val[0]):
            comp.append(np.array([float(v) for v in val[1:]]))
    return ioprof

def get_normioprof(fpath, devname):
    ioprof = []
    for line in open(fpath):
        val = line.split()
        if not val: continue
        elif val[0] == devname:
            tmp = [float(v) for v in val[1:]]
            tmp[4] *= 512 * (10 ** -6) # convert read throughput from sec/s to MB/s
            tmp[5] *= 512 * (10 ** -6) # convert write throughput from sec/s to MB/s
            ioprof.append(tmp)
    return ioprof

def get_ioprof_old(fpath, devname):
    "get histgram of IO profile"
    if devname == "md0": return get_mdioprof(fpath, devname)
    else: return get_normioprof(fpath, devname)

def get_cpuprof_old(fpath, core):
    "get histgram of a CPU core usage"
    cpuprof = []
    for line in open(fpath):
        val = line.split()
        if not val: continue
        elif val[1] == core:
            cpuprof.append([float(v) for v in val[2:]])
    return cpuprof

def get_ioprof(srcpath):
    "get histgram of IO profile"
    ioprofdict = {}
    fo = open(srcpath)
    fo.readline()
    for line in fo:
        val = line.split()
        if not val or ':' in val[0] or '.' in val[0]: continue
        else:
            if val[0] not in ioprofdict: ioprofdict[val[0]] = []
            tmp = [float(v) for v in val[1:]]
            tmp[4] *= 512 * (10 ** -6) # convert read throughput from sec/s to MB/s
            tmp[5] *= 512 * (10 ** -6) # convert write throughput from sec/s to MB/s
            ioprofdict[val[0]].append(tmp)
    fo.close()
    return ioprofdict

def get_cpuprof(srcpath):
    "get histgram of a CPU core usage"
    cpuprofdict = {}
    for line in open(srcpath):
        val = line.split()
        if not val: continue
        elif val[1].isdigit() or "all" == val[1]:
            if val[1] not in cpuprofdict: cpuprofdict[val[1]] = []
            cpuprofdict[val[1]].append([float(v) for v in val[2:]])
    return cpuprofdict

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
            if date: utilhist.append(util)
            date = val[0]
            util = 0.
        if floatpat.search(val[col]):
            tmp = float(val[col])
            if tmp > 2.0: util += tmp
    return utilhist

def get_reliddict(relidfile):
    "get relid dictionary"
    reliddict = {0 : "temporary"}
    for line in open(relidfile):
        vals = [v.strip() for v in line.split('|')]
        if len(vals) != 2 or not vals[0].isdigit(): continue
        else: reliddict[int(vals[0])] = vals[1]
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
                if relname in refdict: refdict[relname] += 1
                else: refdict[relname] = 1
            else:
                assert(time > elapsed)
                for i in range(time - elapsed):
                    refhist.append(refdict)
                    refdict = {}
                refdict[int(vals[5], 16)] = 1
                elapsed = time
    return refhist

def get_iocostprof(srcpath):
    readiocount, writeiocount, readiotime, writeiotime, readioref = range(5)
    iohist = [[0, 0, 0, 0, {}]]
    interval = 10 ** 9
    prevstate = None
    for line in open(srcpath):
        val = line.strip().split()
        if not val:
            continue
        if 'r' == val[1] or 'w' == val[1]:
            if val[1] == prevstate:
                sys.stderr.write("bat IO sequence : line {0}\n".format(i))
                sys.exit(1)
            stime = int(val[0], 16)
            for i in range(stime / interval - (len(iohist) - 1)):
                iohist.append([0, 0, 0, 0, {}])
            idx = readiocount if 'r' == val[1] else writeiocount
            iohist[-1][idx] += 1
            if 'r' == val[1]:
                if int(val[2], 16) in iohist[-1][readioref]:
                    iohist[-1][readioref][int(val[2], 16)] += 1
                else:
                    iohist[-1][readioref][int(val[2], 16)] = 1
        elif 'R' == val[1] or 'W' == val[1]:
            if (val[1].lower() != prevstate) or (int(val[3], 16) != prevblock):
                sys.stderr.write("bat IO sequence : line {0}\n".format(i))
                sys.exit(1)
            ftime = int(val[0], 16)
            idx = readiotime if 'R' == val[1] else writeiotime
            while stime / interval < ftime / interval:
                iohist[-1][idx] += len(iohist) * interval - stime
                stime = len(iohist) * interval
                iohist.append([0, 0, 0, 0, {}])
            iohist[-1][idx] += ftime - stime
        prevstate = val[1]
        prevblock = int(val[3], 16)
    return iohist

def get_cachecoreprof(srcpath, interval):
    selects = ["cycles", "cache-references", "cache-misses"]
    cacheprofdict = {"schema": tuple(["time"] + selects)}
    corepat = re.compile("CPU(\d+)")
    t = 0
    tmpdict = {}
    for line in open(srcpath):
        vals = line.strip().split()
        if not vals or len(vals) < 3: continue
        match = corepat.match(vals[0])
        if match:
            corenum = match.group(1)
            if corenum not in tmpdict: tmpdict[corenum] = [t] +  [-1 for v in selects]
            if vals[2] in selects:
                idx = selects.index(vals[2]) + 1
                tmpdict[corenum][idx] = int(vals[1]) if vals[1].isdigit() else -1
        elif "time" == vals[2] and "elapsed" == vals[3]:
            if tmpdict:
                for k, v in tmpdict.items():
                    if k not in cacheprofdict: cacheprofdict[k] = []
                    cacheprofdict[k].append(tuple(v))
            t += interval
            tmpdict = {}
    return cacheprofdict

def get_cachecoreprof_new(srcpath, interval):
    selects = ["r1cb", "r40cb", "r2cb", "r4cb", "r8cb", "r10cb"]
    cols = ["all_cache_references", "L1D_cache_misses", "L2_cache_misses", "L3_cache_misses"]
    cacheprofdict = {"schema": tuple(["time"] + cols)}
    corepat = re.compile("CPU(\d+)")
    t = 0
    tmpdict = {}
    for line in open(srcpath):
        vals = line.strip().split()
        if not vals or len(vals) < 3: continue
        match = corepat.match(vals[0])
        if match:
            corenum = match.group(1)
            if corenum not in tmpdict: tmpdict[corenum] = [-1 for v in selects]
            if vals[2] in selects:
                idx = selects.index(vals[2])
                tmpdict[corenum][idx] = int(vals[1]) if vals[1].isdigit() else -1
        elif "time" == vals[2] and "elapsed" == vals[3]:
            if tmpdict:
                for k, v in tmpdict.items():
                    if k not in cacheprofdict: cacheprofdict[k] = []
                    vals = [t]
                    vals.append(sum(v)) # all cache ref
                    vals.append(sum(v[1:])) # L1D cache miss
                    vals.append(sum(v[3:])) # L2 cache miss
                    vals.append(sum(v[4:])) # L3 cache miss
                    cacheprofdict[k].append(tuple(vals))
            t += interval
            tmpdict = {}
    return cacheprofdict

def get_cacheaggprof(srcpath, interval):
    cacheprof = []
    t = 0
    cycles, cacheref, cachemiss = 0, 0, 0
    for line in open(srcpath):
        vals = line.strip().split()
        if not vals or len(vals) < 2: continue
        elif "cycles" == vals[1]: cycles = int(vals[0])
        elif "cache-references" == vals[1]: cacheref = int(vals[0])
        elif "cache-misses" == vals[1]: cachemiss = int(vals[0])
        elif "time" == vals[2] and "elapsed" == vals[3]:
            cachehist.append((t, cycles, cacheref, cachemiss))
            t += interval
            cycles, cacheref, cachemiss = 0, 0, 0
    return cacheprof
