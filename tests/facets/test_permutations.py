#from processing import Queue
import gc
import pprint
import sys
import socket
import getopt
import os
import traceback
import time
import unittest
import logging
import string
import subprocess
from test_parameterized_cases import ParameterizedTestCase

sys.path.append('../..')

from ips import Framework
from configobj import ConfigObj

class test_permutations(ParameterizedTestCase):

    def printUsageMessage(self):
        print 'Usage: ips [--create-runspace | --run-setup | --run]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'

    def setUp(self):
        if self.param == None:
            return
        print
        print '------------------------------------------------------------------------------------'
        print 'Parameterization for this test'
        print 'DO_CREATE_RUNSPACE = %s DO_RUN_SETUP = %s DO_RUN = %s' % \
            (self.param.do_create_runspace, self.param.do_run_setup, self.param.do_run)
        print 'CREATE_RUNSPACE_DONE = %s RUN_SETUP_DONE = %s RUN_DONE = %s' % \
            (self.param.create_runspace_done, self.param.run_setup_done, self.param.run_done)
        print '------------------------------------------------------------------------------------'
#       self.fwk = Framework(self.param.do_create_runspace, 
#                       self.param.do_run_setup,
#                       self.param.do_run, 
#                       self.param.cfgFile_list, 
#                       self.param.log_file, 
#                       self.param.platform_filename)

#   def tearDown(self):
#       self.fwk = None

    def test_given_parameters(self):

        if self.param == None:
            return
        # create the checklist.conf that Framework will use
#       checklist_file_name = os.path.join(self.fwk.sim_root, 'checklist.conf')
        sim_conf = ConfigObj(self.param.cfgFile_list[0], interpolation='template',
                         file_error=True)
        checklist_file_name = os.path.join(sim_conf['SIM_ROOT'], 'checklist.conf')
        try:
            checklist_file = open(checklist_file_name, 'w')
        except IOError, ioe:
            raise
        if self.param.create_runspace_done:
            checklist_file.write('CREATE_RUNSPACE = DONE\n')
        else:
            checklist_file.write('CREATE_RUNSPACE = NOT_DONE\n')
        if self.param.run_setup_done:
            checklist_file.write('RUN_SETUP = DONE\n')
        else:
            checklist_file.write('RUN_SETUP = NOT_DONE\n')
        if self.param.run_done:
            checklist_file.write('RUN = DONE\n')
        else:
            checklist_file.write('RUN = NOT_DONE\n')
        checklist_file.flush()
        checklist_file.close()

        call_args = []
        call_args.append(sim_conf['IPS_ROOT'] + '/framework/src/ips.py')
        if self.param.do_create_runspace:
            call_args.append('--create-runspace')
        if self.param.do_run_setup:
            call_args.append('--run-setup')
        if self.param.do_run:
            call_args.append('--run')
        
        cfg_files_str = '--simulation=' + self.param.cfgFile_list[0]
        for file in self.param.cfgFile_list[1:]:
            cfg_files_str += ',' + file
        call_args.append(cfg_files_str)

        call_args.append('--platform=' + self.param.platform_filename)
        call_args.append('--log=' + self.param.log_file)

        print string.join(call_args, ' ')
        #test must return true if nothing bad happened, false otherwise
#       self.assertTrue(self.fwk.run(), 'error in running fwk')
        self.assertEquals(subprocess.call(call_args), 0, 'error in running IPS')

        # set correct result of CREATE_RUNSPACE parameterization
        if self.param.do_create_runspace or self.param.create_runspace_done:
            self.create_runspace_result = 'DONE'
        else:
            self.create_runspace_result = 'NOT_DONE'

        # set correct result of RUN_SETUP parameterization
        if self.param.do_run_setup and self.create_runspace_result == 'DONE':
            self.run_setup_result = 'DONE'
        else:
            self.run_setup_result = 'NOT_DONE'
            
        # set correct result of RUN parameterization
        if self.param.do_run and self.run_setup_result == 'DONE':
            self.run_result = 'DONE'
        else:
            self.run_result = 'NOT_DONE'

        # read in the values the Framework wrote out
        self.conf = ConfigObj(checklist_file_name, 
                         interpolation = 'template',
                         file_error = True)

        self.assertEquals(self.create_runspace_result, self.conf['CREATE_RUNSPACE'])
        self.assertEquals(self.run_setup_result, self.conf['RUN_SETUP'])
        self.assertEquals(self.run_result, self.conf['RUN'])

