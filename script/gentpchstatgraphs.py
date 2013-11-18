#! /usr/bin/env python

import sys, os, glob
from dbprofutils import get_reliddict
import drawiocost, drawioref

import drawio, drawcpu, drawcache, generategraphsdir

def gen_allgraph(rootdir, reliddict = None, terminaltype = "png"):
    statfiles = generategraphsdir.search_statfiles(rootdir)
    generategraphsdir.generate_allstatgraphs(statfiles, terminaltype = terminaltype)
    for d in glob.iglob(rootdir + "/workmem*"):
        for dd in glob.iglob(d + "/[0-9]*"):
            outprefix = dd + "/default"
            for f in glob.iglob(dd + "/*.res"):
                outprefix = os.path.splitext(f)[0] + os.path.basename(d)
            for f in glob.iglob(dd + "/*.time"):
                outprefix = os.path.splitext(f)[0] + os.path.basename(d)
            for f in glob.iglob(dd + "/trace_*.iocosthist"):
                iocostprof = [[float(v) for v in line.strip().split()] for line in open(f)]
                output = "{0}_iocosthist.{1}".format(outprefix, terminaltype)
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
                    output = "{0}_iorefhist.{1}".format(outprefix, terminaltype)
                    drawioref.plot_tblrefhist(reliddict, iorefhist, output, terminaltype)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write(
            "Usage : {0} rootdir [relidfile] [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    rootdir = sys.argv[1]
    relidfile = sys.argv[2] if len(sys.argv) >= 3 else None
    terminaltype = sys.argv[3] if len(sys.argv) >= 4 else "png"
    if terminaltype != "png" and terminaltype != "eps":
        sys.stderr.write("wrong terminal type\n")
        sys.exit(1)

    reliddict = get_reliddict(relidfile) if relidfile else None
    gen_allgraph(rootdir, reliddict, terminaltype)
