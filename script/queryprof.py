#! /usr/bin/env python

import sys, os, tempfile, time, subprocess

outputdir = "/data/local/keisuke/tpch"

if __name__ == "__main__":
    for i in [1] + range(3, 11):
        tmpfo = tempfile.TemporaryFile()
        pid = os.fork()
        if pid == 0:
            while (True):
                for line in open("/proc/diskstats"):
                    k, v = line.split(None, 3)[2:]
                    if (k == "md0"):
                        tmpfo.write(v)
                time.sleep(1)

        else:
            outfo = open("{0}/{1}.res".format(outputdir, i), "w")
            stime = time.time()
            p = subprocess.Popen(["psql", "-d", "tpch", "-f", "{0}.sql".format(i)],
                                 stdout = outfo)
            p.wait()
            ftime = time.time()
            elapsed = ftime - stime
            outfo.write("\nelapsed time : {0}\n".format(elapsed))
            outfo.close()

            os.kill(pid, 15)

            tmpfo.seek(0)
            prev = [long(v) for v in tmpfo.readline().split()]
            with open("{0}/{1}ioprof.txt".format(outputdir, i), "w") as proffo:
                for line in tmpfo:
                    data = [long(v) for v in line.split()]
                    out = [d - p if i != 8 else d
                           for i, (d, p) in enumerate(zip(data, prev))]
                    proffo.write(' '.join([str(v) for v in out]))
                    prev = data[:]
            tmpfo.close()
