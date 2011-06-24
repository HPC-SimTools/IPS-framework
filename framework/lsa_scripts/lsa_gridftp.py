#!/usr/bin/python

"""
Overall script to run LSA component system.  This would be the core
Python/Jython script in the portal, but with the file moves being
done by the data manager and the information being published to the
event channel. 

This will run make on a component that does not have the executable
existant. Also, it will seize your firefox window to display the final
results.

    ----------------------------------
    IU Fusion Simulation Project Team:
    ----------------------------------
    Randall Bramley
    Joseph Cottam
    Anne Faber
    Samantha Foley
    Nisha Gupta
    Yu (Marie) Ma
    David Mack (alumnus)
    Yongquan (Cathy) Yuan (alumnus)

    Department of Computer Science
    Indiana University, Bloomington

Modifications: Fri May 12 10:25:13 EDT 2006

Set up to run the diagram on whiteboard:
                    BasicInfo
                   /        \
                  /          \
                Scale       Reorder
               /    \       /     \
          Splib  SuperLU  Splib  SuperLU

Modifications: Wed Jun 14 10:25:43 EDT 2006
  Added Samantha, alphabetized list of people, removed email address

"""

import os, sys            
from posixpath import isfile 
from time import time, ctime

user = os.environ['USER']
#host = os.environ['HOSTNAME']
host = "odin"
rundir = "/san/fsp/faber/lsa/"
print 'Cleaning directories'
cmd="./clean_lsa.sh"
os.system(cmd)

print 'Starting overall LSA script\n' 
print 'user:', user
print 'path:', os.getcwd()
print 'time:', ctime(time())

print '------------------ Starting BasicInfo component'
#cmd = '(cd BasicInfo ; ln -sf ../mat.cfd mat.in; ./SWIM_runit.py)'
cmd = '(globus-url-copy gsiftp://' + host  + rundir + 'mat.in gsiftp://' + host + rundir + 'BasicInfo/mat.in)'
print 'executing: ', cmd
os.system(cmd)

#run BasicInfo
#cmd = 'globus-job-run ' + host + ' -d ' + rundir + 'BasicInfo -env SWIM_PYTHON=/san/cca/Python/bin/python USER=' + user + ' ' + rundir + 'BasicInfo/SWIM_runit.py'
cmd = 'globus-job-run ' + host + ' -d ' + rundir + 'BasicInfo -env USER=' + user + ' ' + rundir + 'BasicInfo/SWIM_runit.py'
print 'executing: ', cmd
os.system(cmd)

"""

#Read in BasicInfo subdirectory location
subdirloc = open("BasicInfo/newdirfile","r")
BI_dir=subdirloc.readline()
subdirloc.close()

print '------------------ Starting Scale component'
#cmd = '(cp -f BasicInfo/' + user +'/*/mat.in Scale; cd Scale; ./runit.py)'
cmd= '(globus-url-copy gsiftp://' + host + BI_dir + '/mat.in gsiftp://' + host + os.getcwd() + '/Scale/mat.in)'
print 'executing: ', cmd
os.system(cmd)

os.chdir("Scale")
cmd='./runit.py'
print 'executing: ', cmd
os.system(cmd)
os.chdir("..")

#Read in Scale subdirectory location
subdirloc = open("Scale/newdirfile","r")
Scale_dir=subdirloc.readline()
subdirloc.close()
print "Scale directory: " + Scale_dir

print '------------------- Moving data from Scale to Splib'
#cmd = '(cp -f Scale/' + user + '/*/mat.out Splib/mat.in)'
cmd= '(globus-url-copy gsiftp://' + host + Scale_dir + '/mat.out gsiftp://' + host + os.getcwd() + '/Splib/mat.in)'
print 'executing: ', cmd
os.system(cmd)

print '--------------------------------------  Moving data from Scale to SuperLU'
#cmd = '(cp -f Scale/' + user + '/*/mat.out SuperLU/mat.in)'
cmd= '(globus-url-copy gsiftp://' + host + Scale_dir + '/mat.out gsiftp://' + host + os.getcwd() + '/SuperLU/mat.in)'
print 'executing: ', cmd
os.system(cmd)

print '------------------- Now run the reorder branch of the tree'
#cmd = '(cp -f BasicInfo/' + user + '/*/mat.in Reorder; cd Reorder; ./runit.py)'
cmd='(globus-url-copy gsiftp://' + host + BI_dir + '/mat.in gsiftp://' + host + os.getcwd() + '/Reorder/mat.in)'
print 'executing: ', cmd
os.system(cmd)
os.chdir("Reorder")
cmd='./runit.py'
print 'executing: ', cmd
os.system(cmd)
os.chdir("..")

#Read in Reorder subdirectory location
subdirloc = open("Reorder/newdirfile","r")
Reorder_dir=subdirloc.readline()
subdirloc.close()

print '------------------ Starting Splib component'
#cmd = '(cp -f Reorder/' + user + '/*/mat.out Splib; cd Splib; ./runit.py)'
cmd='(globus-url-copy gsiftp://' + host + Reorder_dir + '/mat.out gsiftp://' + host + os.getcwd() + '/Splib/mat.in)'
print 'executing: ', cmd
os.system(cmd)
os.chdir("Splib")
cmd='./runit.py'
print 'executing: ', cmd
os.system(cmd)
os.chdir("..")

print '------------------ Starting SuperLU component'
#cmd = '(cp -f Reorder/' + user + '/*/mat.out SuperLU; cd SuperLU; ./runit.py)'
cmd='(globus-url-copy gsiftp://' + host + Reorder_dir + '/mat.out gsiftp://' + host + os.getcwd() + '/SuperLU/mat.in)'
print 'executing: ', cmd
os.system(cmd)
os.chdir("SuperLU")
cmd='./runit.py'
print 'executing: ', cmd
os.system(cmd)
os.chdir("..")

"""
print 'script done'
