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

sys.path.append('../..')

from ips import Framework
from configobj import ConfigObj

class test_permutations(unittest.TestCase):

    def __init__(self, methodName='runTest',
                 do_create_runspace=True, do_run_setup=True, do_run=True,
                 create_runspace_done=True, run_setup_done=True, run_done=True):
        super(test_permutations, self).__init__(methodName)
        self.do_create_runspace = do_create_runspace
        self.do_run_setup = do_run_setup
        self.do_run = do_run
        self.create_runspace_done = create_runspace_done
        self.run_setup_done = run_setup_done
        self.run_done = run_done

    def printUsageMessage(self):
        print 'Usage: ips [--create-runspace | --run-setup | --run]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'

    def suite(self):
        return unittest.TestSuite(map(test_permutations, ['runTest']))

    def runTest(self):
        print
        cfgFile_list = []
        cfgFile_list.append('basic_serial1_iter.conf')
        platform_filename = 'iter.conf'
        log_file = 'log_test_basic_serial1_on_iter.log'
        #log_file = open(os.path.abspath('log_test_basic_serial1_on_iter.log'), 'w')
        #log_file = sys.stdout

        # create framework with config file
        print '------------------------------------------------------------------------------------'
        print 'Parameterization for this test'
        print 'DO_CREATE_RUNSPACE = %s DO_RUN_SETUP = %s DO_RUN = %s' % \
            (self.do_create_runspace, self.do_run_setup, self.do_run)
        print 'CREATE_RUNSPACE_DONE = %s RUN_SETUP_DONE = %s RUN_DONE = %s' % \
            (self.create_runspace_done, self.run_setup_done, self.run_done)
        print '------------------------------------------------------------------------------------'
        fwk = Framework(self.do_create_runspace, 
                        self.do_run_setup,
                        self.do_run, 
                        cfgFile_list, 
                        log_file, 
                        platform_filename)
        checklist_file_name = os.path.join(fwk.sim_root, 'checklist.conf')
        checklist_file = open(checklist_file_name, 'w')
        if self.create_runspace_done:
            checklist_file.write('CREATE_RUNSPACE = DONE\n')
        else:
            checklist_file.write('CREATE_RUNSPACE = NOT_DONE\n')
        if self.run_setup_done:
            checklist_file.write('RUN_SETUP = DONE\n')
        else:
            checklist_file.write('RUN_SETUP = NOT_DONE\n')
        if self.run_done:
            checklist_file.write('RUN = DONE\n')
        else:
            checklist_file.write('RUN = NOT_DONE\n')
        checklist_file.flush()
        checklist_file.close()
        #absCfgFile_list = [os.path.abspath(cfgFile) for cfgFile in cfgFile_list]

        #test must return true if nothing bad happened, false otherwise
        self.assertTrue(fwk.run(), 'error in running fwk')

        # set correct result of CREATE_RUNSPACE parameterization
        if self.do_create_runspace or self.create_runspace_done:
            self.create_runspace_result = 'DONE'
        else:
            self.create_runspace_result = 'NOT_DONE'

        # set correct result of RUN_SETUP parameterization
        if self.do_run_setup and self.create_runspace_result == 'DONE':
            self.run_setup_result = 'DONE'
        else:
            self.run_setup_result = 'NOT_DONE'
            
        # set correct result of RUN parameterization
        if self.do_run and self.run_setup_result == 'DONE':
            self.run_result = 'DONE'
        else:
            self.run_result = 'NOT_DONE'

        # read in the values the Framework wrote out
        conf = ConfigObj(checklist_file_name, 
                         interpolation = 'template',
                         file_error = True)
        self.assertEquals(self.create_runspace_result, conf['CREATE_RUNSPACE'])
        self.assertEquals(self.run_setup_result, conf['RUN_SETUP'])
        self.assertEquals(self.run_result, conf['RUN'])
        return 0

