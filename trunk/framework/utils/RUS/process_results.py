'''
This Python script processes a list of results files (rwfile.*) produced 
from a series of RUS runs, and produces a graph using gnuplot.

This must be run from the same directory as plot.sh.

8/6/2010
Samantha Foley
'''

import sys, os
import matplotlib
import subprocess

def shift_values(fname):
    f = open(fname, 'r')
    dir, experiment = fname.split("rwfile.")
    lines = f.readlines()
    f.close()
    c1 = []
    c2 = []
    for i in range(len(lines)):
        x = lines[i].split()
        print x
        c1.append(int(x[0]))
        c2.append(float(x[1]))

    print c1

    for i in range(len(lines) - 1):
        c1[i] = c1[i+1]

    f = open("rwfile." + experiment, 'w')
    for i in range(len(c1)):
        print >> f, c1[i], c2[i]

    f.close()


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        try:
            shift_values(arg)
            dir, experiment = arg.split("rwfile.")
            subprocess.call(["./plot.sh", experiment])
            matplotlib.pyplot.plotfile(arg,(0,1),  newfig = True)
            #subprocess.call(["rm", "rwfile."+experiment])
        except:
            print "problem processing data for %s" % arg
            raise
        
