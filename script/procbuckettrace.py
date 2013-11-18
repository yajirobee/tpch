#! /usr/bin/env python

import sys, os, glob, re, sqlite3

def proc_suffix(val, prefix):
    if 'k' == prefix: val *= 2 ** 10
    elif 'M' == prefix: val *= 2 ** 20
    elif 'G' == prefix: val *= 2 ** 30
    else:
        sys.stderr.write("wrong prefix\n")
        sys.exit(1)
    return val

def proc_buckettracefile(tracefile):
    reslist = []
    for line in open(tracefile):
        vals = line.strip().split()
        if vals[1] != 'S': continue
        resdict = None
        for d in reslist:
            if d["nbatch"] == vals[2] and d["nbucket"] == vals[3]:
                resdict = d
                break
        if not resdict:
            reslist.append({"nbatch": vals[2], "nbucket": vals[3], "size": vals[4],
                            "sum": 0, "count": 0})
            resdict = reslist[-1]
        resdict["sum"] += int(vals[6], 16)
        resdict["count"] += 1
    return reslist

def proc_directory(directory):
    sys.stdout.write("processing {0}\n".format(directory))
    match = re.search("workmem(\d+)(k|M|G)B", directory)
    workmem = proc_suffix(int(match.group(1)), match.group(2))
    files = glob.glob(directory + "/trace_*.log")
    assert files, "tracefile dose not exist"
    f = max(files, key = os.path.getsize)
    res = proc_buckettracefile(f)
    return workmem, res

def main(rootdir):
    dirs = []
    for d in glob.iglob(rootdir + "/workmem*"):
        dirs.extend(glob.glob(d + "/[0-9]*"))
    allres = [proc_directory(d) for d in dirs]
    allres = sorted(allres, key = lambda x:x[0])

    conn = sqlite3.connect(rootdir + "/spec.db")
    bucketinfotbl = "bucketinfo"
    bucketinfocols = ("workmem integer",
                      "nbatch integer",
                      "nbucket integer",
                      "size integer",
                      "sum integer",
                      "count integer")
    tbldict = {bucketinfotbl: bucketinfocols}
    for k, v in tbldict.items():
        conn.execute("create table {0} ({1})".format(k, ','.join(v)))
    query = "insert into {0} values ({1})"
    for res in allres:
        for d in res[1]:
            conn.execute(query.format(bucketinfotbl, ','.join('?' * len(bucketinfocols))),
                         (res[0], int(d["nbatch"], 16), int(d["nbucket"], 16),
                          int(d["size"], 16), d["sum"], d["count"]))
        conn.commit()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        rootdir = sys.argv[1]
    else:
        sys.stderr.write("Usage : {0} rootdir\n".format(sys.argv[0]))
        sys.exit(0)

    main(rootdir)
