#! /usr/bin/env python

import sys
import os
import subprocess
import getopt
import shutil

IPS_ROOT=''
SIM_ROOT=''
CURRENT_TIME = ''
COMPONENT_CLASS = 'state'
COMPONENT_SUBCLASS = 'utilities'
COMPONENT_NAME = 'profile'
NUM_PROC=1
#INPUT_FILES = ['aorsa2d.in', 'grfont.dat', 'ZTABLE.TXT']
OUTPUT_FILES = []

def printUsageMessage():
   print 'Usage: %s --ipsroot=FULL_IPS_ROOT_PATH --simroot=FULL_PATH_TO_CURRENT_SIMULATION --curtime=CURRENT_TIME_IN_MSEC --nproc=NUM_PROCESSORS' % (sys.argv[0])


def main(argv=None):
   global IPS_ROOT, SIM_ROOT, COMPONENT_CLASS, COMPONENT_SUBCLASS, COMPONENT_NAME, INPUT_FILES, NUM_PROC, CURRENT_TIME
# Parse command line arguments
   if argv is None:
      argv = sys.argv
      try:
         opts, args = getopt.gnu_getopt(argv[1:],'', ["ipsroot=", "simroot=", "curtime=", "nproc="])
      except getopt.error, msg:
         print 'Exception'
         printUsageMessage()
         return 1 
   for arg,value in opts:
      print arg, value
      if (arg == '--ipsroot'):
         IPS_ROOT = value
      elif (arg == '--simroot'):
         SIM_ROOT = value
      elif (arg == '--curtime'):
         CURRENT_TIME = value
      elif (arg == '--nproc'):
         NUM_PROC = value
   if (IPS_ROOT == '' or SIM_ROOT == '' or CURRENT_TIME=='' ):
      printUsageMessage()
      return 1
   
#   prepare_input = os.path.join(IPS_ROOT, 'bin', 'prepare_aorsa_input')
#   process_output  = os.path.join(IPS_ROOT,'bin', 'process_aorsa_output')
   prepare_input = ''
   process_output  = ''
   profile_bin = os.path.join(IPS_ROOT, 'bin', 'change_power')
   
#
# Check existence and/or create working directory for the current run
   workdir = SIM_ROOT + '/work/'+COMPONENT_CLASS+'/'+COMPONENT_SUBCLASS+'/'+COMPONENT_NAME
   try:
      os.chdir(workdir)
   except OSError, (errno, strerror):
      print 'Directory %s does not exist - will attempt creation' % (workdir)
      try:
         os.makedirs(workdir)
      except OSError, (errno, strerror):
         print 'Error creating directory %s : %s' % (workdir, strerror)
         return 1
      os.chdir(workdir)
 
# Copy current and prior state over to working directory
   statedir = os.path.join(SIM_ROOT, 'work', 'plasma_state')
   cur_state = 'cur_state.cdf'
   prior_state = 'prev_state.cdf'
   for f in [cur_state, prior_state]:
      try:
	      shutil.copyfile(os.path.join(statedir,f), os.path.join(workdir,f))
      except IOError, (errno, strerror):
         print 'Error copying file %s to work directory %s : %s' % (f, workdir, strerror)
         return 1
       
# Call prepare_aorsa-input
   if(prepare_input != ''):
      retcode = subprocess.call([prepare_input])
      if (retcode != 0):
         print 'Error in call to prepare_aorsa_input'
         return 1

# Call change_power 
   retcode = subprocess.call([profile_bin])
   if (retcode != 0):
      print 'Error in call to xaorsa2d'
      return 1  

# How do we know that th ecall succeeded ??

# Call process_output and copy files over 
   if(process_output != ''):
      retcode = subprocess.call([process_output])
      if (retcode != 0):
         print 'Error in call to %s' % (process_output)
         return 1  

# Update (original) plasma state
   for f in ['cur_state.cdf', 'prev_state.cdf']:
      cmd = ['/bin/cp', '-f', f, statedir]
      retcode = subprocess.call(cmd)
      if (retcode != 0):
         print 'Error copying file %s to state directory %s' %(f, statedir)
         return 1

# Copy simulation results over to SIM_ROOT/simulation_results/history/current_time

   targetdir = os.path.join(SIM_ROOT ,'simulation_results', 'history', CURRENT_TIME , 'components' , COMPONENT_CLASS, COMPONENT_SUBCLASS, COMPONENT_NAME)
   try:
      os.makedirs(targetdir)
   except OSError, (errno, strerror):
      if (errno != 17):    #Directory exists
         print 'Error accessing directory %s : %s' % (targetdir, strerror)
         return 1
      pass   
   for f in OUTPUT_FILES:
      try:
	      shutil.copyfile(f, os.path.join(targetdir,f))
      except IOError, (errno, strerror):
         print 'Error copying file %s to %s : %s' % (f, targetdir, strerror)
         return 1
 
if __name__ == "__main__":
    sys.exit(main())
