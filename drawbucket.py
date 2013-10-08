#! /usr/bin/env python

import sys, os, sqlite3
from plotutil import query2gds, gpinit, ceiltop

slide = False

def draw_bucket(dbpath, terminaltype = "png"):
    conn = sqlite3.connect(dbpath)
    gp = gpinit(terminaltype)
    dirname = os.path.dirname(os.path.abspath(dbpath))
    output = "{0}/bucketscan.{1}".format(dirname, terminaltype)
    gp('set output "{0}"'.format(output))
    gp.xlabel("work\_mem [byte]")
    gp('set ylabel "# of bucket scan"')
    gp('set y2label "# of partition * # of bucket"')
    gp('set format x "%.0b%B"')
    gp('set logscale x 2')
    gp('set ytics nomirror')
    gp('set grid xtics noytics noy2tics')
    gp('set yrange[0:*]')
    y2max = conn.execute("select max(nbatch * nbucket) from bucketinfo").fetchone()[0]
    y2max = ceiltop(y2max)
    gp('set y2range[0:{0}]'.format(y2max))
    gp('set y2tics {0}'.format(y2max / 10))
    if slide:
        if "eps" == terminaltype:
            gp('set termoption font "Times-Roman,28"')
            plotprefdict = {"with_" : "linespoints lt 1 lw 6" }
        elif "png" == terminaltype:
            gp('set termoption font "Times-Roman,18"')
            plotprefdict = {"with_" : "linespoints lw 2"}
    else:
        plotprefdict = {"with_" : "linespoints" }
    query = "select workmem, {0} from bucketinfo order by workmem"
    gds = []
    gds.extend(query2gds(conn, query.format("sum"),
                         title = "nbucketscan", axes = "x1y1", **plotprefdict))
    gds.extend(query2gds(conn, query.format("nbatch * nbucket"),
                         title = "npart * nbucket", axes = "x1y2", **plotprefdict))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        dbpath = sys.argv[1]
        terminaltype = "png"
    elif len(sys.argv) == 3:
        dbpath = sys.argv[1]
        terminaltype = sys.argv[2]
    else:
        sys.stdout.write(
            "Usage : {0} dbpath [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    draw_bucket(dbpath, terminaltype)
