#! /usr/bin/env python

import sys
import os
import subprocess
import getopt

IPS_ROOT=''
SIM_ROOT=''
COMPONENT_CLASS = 'state'
COMPONENT_SUBCLASS = 'utilities'
COMPONENT_NAME = 'profile'
INPUT_FILES = []

def printUsageMessage():
   print 'Usage: %s --ipsroot=FULL_IPS_ROOT_PATH --simroot=FULL_PATH_TO_CURRENT_SIMULATION' % (sys.argv[0])


def main(argv=None):
   global IPS_ROOT, SIM_ROOT, COMPONENT_CLASS, COMPONENT_SUBCLASS, COMPONENT_NAME, INPUT_FILES
# Parse command line arguments
   if argv is None:
      argv = sys.argv
      try:
         opts, args = getopt.gnu_getopt(argv[1:],'', ["ipsroot=", "simroot="])
      except getopt.error, msg:
         printUsageMessage()
         return 1 
   for arg,value in opts:
      print arg, value
      if (arg == '--ipsroot'):
         IPS_ROOT = value
      elif (arg == '--simroot'):
         SIM_ROOT = value
   if (IPS_ROOT == '' or SIM_ROOT == ''):
      printUsageMessage()
      return 1
#
#Assumptions:
#  1- Initial input files (files that do not change with each time step) are located
#     along with the component sources (e.g. in IPS_ROOT/components/rf/aorsa)
#  2- Input files are copied (or soft linked) to the work directory of 
#     the current simulation run
#  3- The work directory for the current component in the current simultaion run is 
#      SIM_ROOT/work/COMPONENT_CLASS/COMPONENT_SUBCLASS/COMPONENT_NAME 
#      (e.g. IPS_RUN_XYZ/work/rf/ic/aorsa)
#
   inputFiles_src = os.path.join(IPS_ROOT, 'components', COMPONENT_CLASS, COMPONENT_NAME )
#
# Note: aorsa2d.in has a static part AND a  dynamic part that is overwritten  as part
#       of th ecall to prepare_aorsa_input
   
#
# Check existence and/or create working directory for the current run
   workdir = os.path.join(SIM_ROOT, 'work', COMPONENT_CLASS, COMPONENT_SUBCLASS, COMPONENT_NAME)
   try:
      os.chdir(workdir)
   except OSError, (errno, strerror):
      print 'Directory %s does not exist - will attempt creation' % (workdir)
      try:
         os.makedirs(workdir)
      except OSError, (errno, strerror):
         print 'Error creating directory %s : %s' % (workdir, strerror)
         return 1

# Copy static files into working directory      
   for f in [inputFiles_src +'/'+ file for file in INPUT_FILES] :
      cmd = ['/bin/cp', f, workdir]
      retcode = subprocess.call(cmd)
      if (retcode != 0):
         print 'Error copying file %s to work directory %s' %(f, workdir)
         return 1
       
if __name__ == "__main__":
    sys.exit(main())
