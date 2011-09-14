#! /usr/bin/env python

import sys
import os
import subprocess
import getopt
import shutil
import math

IPS_ROOT=''
SIM_ROOT=''
CURRENT_TIME = ''
COMPONENT_CLASS = ''
COMPONENT_SUBCLASS = ''
COMPONENT_NAME = ''
NUM_PROC=1
INPUT_FILES = []
OUTPUT_FILES = []

# CComponents dictionary: list entries: [COOMPONENT_CLASS, COMPONENT_SUBCLASS, COMPONET_NAME]
# COMPONENTS = {'RF':['rf','ic','aorsa'], 'PROFILE':['state','utilities', 'profile']}
COMPONENTS = {'EPA':['epa','','']}

def printUsageMessage():
    print 'Usage: %s --ipsroot=FULL_IPS_ROOT_PATH  --simroot=SIMULATION_ROOT --nproc=NUM_PROCESSORS' % (sys.argv[0])


def main(argv=None):
    global IPS_ROOT, SIM_ROOT, COMPONENTS, COMPONENT_CLASS, COMPONENT_SUBCLASS, COMPONENT_NAME, INPUT_FILES, NUM_PROC
# Parse command line arguments
    if argv is None:
        argv = sys.argv
        try:
            opts, args = getopt.gnu_getopt(argv[1:],'', ["ipsroot=", "simroot=", "nproc="])
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
        elif (arg == '--nproc'):
            NUM_PROC = value
    if (IPS_ROOT == '' or SIM_ROOT == '' or NUM_PROC=='' ):
        printUsageMessage()
        return 1

#
#  Check existence and/or create working directory for the current driver run
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
        os.chdir(workdir)

#  Copy input files into working directory
    inputFiles_src = os.path.join(IPS_ROOT, 'components', COMPONENT_CLASS, COMPONENT_NAME)
    for f in INPUT_FILES :
        try:
            shutil.copyfile(os.path.join(inputFiles_src, f), os.path.join(workdir, f))
        except IOError, (errno, strerror):
            print 'Error copying file %s to %s : %s' % (f, workdir, strerror)
            return 1
#
# Initialize the state
    stateinit_bin = os.path.join(IPS_ROOT,'bin', 'swim_state_init')
    statedir = os.path.join(SIM_ROOT, 'work', 'plasma_state')
    try:
        os.makedirs(statedir)
    except OSError, (errno, strerror):
        if (errno != 17):
            print 'Error creating state directory %s : %d %s' % (statedir, errno, strerror)
            return 1

#   retcode = subprocess.call([stateinit_bin])
#   if (retcode != 0):
#      print 'Error in call to swim_state_init'
#      return 1
#   cur_state = 'plasma_state.cdf'
#   prior_state = 'prior_state.cdf'
#   for f in [cur_state, prior_state]:
#      try:
#         shutil.copyfile(os.path.join(workdir,f), os.path.join(statedir,f))
#      except IOError, (errno, strerror):
#         print 'Error copying file %s to state directory %s : %s' % (f, statedir, strerror)
#         return 1

# Set component scripts
    epaComponent = COMPONENTS['EPA']
    epa_init = 'init_'+ epaComponent[0]
    epa_step = 'step_'+ epaComponent[0]
    if epaComponent[1] is not '':
        epa_init = epa_init +'_'+epaComponent[1]
        epa_step = epa_step +'_'+epaComponent[1]
    if epaComponent[2] is not '':
        epa_init = epa_init +'_'+epaComponent[2]
        epa_step = epa_step +'_'+epaComponent[2]
    epa_init = epa_init +'.py'
    epa_step = epa_step +'.py'
    epa_init = os.path.join(IPS_ROOT, 'bin', epa_init)
    epa_step = os.path.join(IPS_ROOT, 'bin', epa_step)

# Initialize all components
    for c in [epa_init]:
        print 'Calling ', c
        retcode = subprocess.call([c, '--ipsroot', IPS_ROOT, '--simroot', SIM_ROOT])
        if (retcode != 0):
            print 'Error in call to %s' % (c)
            return 1

# Main simulation loop
    tfirst= 0.0
#  time in seconds
    tlist = [3.4, 3.5, 3.7]
    tlist_str = ['%.2f'%t for t in tlist]
    for t in tlist_str:
        tnow = str(float(t)+float(tfirst))
        print 'Current time = ', tnow
# call PROFILE component on 1 processors
        cmd = [epa_step,'--ipsroot='+IPS_ROOT,'--simroot='+SIM_ROOT,'--curtime='+tnow, '--nproc=1']
        retcode = subprocess.call(cmd)
        if (retcode != 0):
            print 'Error in call to %s' % (epa_step)
            return 1

if __name__ == "__main__":
    sys.exit(main())
