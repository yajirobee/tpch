#! /usr/bin/env python

import sys, os, sqlite3, Gnuplot
from plotutil import query2gds, query2data, gpinit, ceiltop

slide = False
slide = 1

def draw_bucket(dbpath, terminaltype = "png"):
    conn = sqlite3.connect(dbpath)
    gp = gpinit(terminaltype)
    dirname = os.path.dirname(os.path.abspath(dbpath))
    output = "{0}/bucketscan.{1}".format(dirname, terminaltype)
    gp('set output "{0}"'.format(output))
    gp('set key inside left top')
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
            plotprefdict = {"with_" : "points lt 1 lw 6" }
        elif "png" == terminaltype:
            gp('set termoption font "Times-Roman,18"')
            plotprefdict = {"with_" : "points lw 2"}
    else:
        plotprefdict = {"with_" : "points" }
    query = "select workmem, {0} from bucketinfo order by workmem"
    gds = []
    datalist = query2data(conn, query.format("sum"))
    gds.append(Gnuplot.Data(datalist[0], datalist[1], [v / 4 for v in datalist[0]],
                            title = "nbucketscan", axes = "x1y1",
                            with_ = 'boxes lc rgb "blue" fs solid border lc rgb "black"'))
    gds.extend(query2gds(conn, query.format("nbatch * nbucket"),
                         title = "npartition * nbucket", axes = "x1y2", **plotprefdict))
    gp.plot(*gds)
    sys.stdout.write("output {0}\n".format(output))
    gp.close()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stdout.write(
            "Usage : {0} dbpath [eps|png]\n".format(sys.argv[0]))
        sys.exit(0)

    dbpath = sys.argv[1]
    terminaltype = sys.argv[2] if len(sys.argv) >= 3 else "png"
    if terminaltype != "png" and terminaltype != "eps":
        sys.stdout.write("wrong terminal type\n")
        sys.exit(1)

    draw_bucket(dbpath, terminaltype)
