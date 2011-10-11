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
from test_permutations import test_permutations
from test_parameterized_cases import ParameterizedTestCase

sys.path.append('../..')

from ips import Framework
from configobj import ConfigObj

"""
    This will be the test harness for the various comprehensive tests.
    Need to do:
    * develop a way to set up different test scenarios (input files and expected results) along with descriptions
"""

class testIPS(unittest.TestCase):

    class Parameterization(object):
        """ Structure to hold the parameterization of 
            a Framework object
        """
        def __init__(self):
            self.do_create_runspace = None
            self.do_run_setup = None
            self.do_run = None
            self.create_runspace_done = None
            self.run_setup_done = None
            self.run_done = None
            self.cfgFile_list = []
            self.log_file = None
            self.platform_filename = None

    def printUsageMessage(self):
        print 'Usage: ips [--create-runspace | --run-setup | --run]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'

    """
    def test_basic_serial1(self):
        cfgFile_list = []
        cfgFile_list.append('basic_serial1_laptop.conf')
        platform_filename = 'laptop.conf'
        log_file = 'log_test_basic_serial1_on_laptop.log'
        #log_file = open(os.path.abspath('log_test_basic_serial1_on_laptop.log'), 'w')
        #log_file = sys.stdout

        # create framework with config file
        print '------------------------------------------------------------------------------------'
        print 'Parameterization for this test'
        print 'DO_CREATE_RUNSPACE = %s DO_RUN_SETUP = %s DO_RUN = %s' % \
            (False, True, True)
        print 'CREATE_RUNSPACE_DONE = %s RUN_SETUP_DONE = %s RUN_DONE = %s' % \
            (True, True, True)
        print '------------------------------------------------------------------------------------'
        fwk = Framework(False, True, True, cfgFile_list, log_file, platform_filename)
        checklist_file_name = os.path.join(fwk.sim_root, 'checklist.conf')
        checklist_file = open(checklist_file_name, 'w')
        checklist_file.write('CREATE_RUNSPACE = DONE\n')
        checklist_file.write('RUN_SETUP = DONE\n')
        checklist_file.write('RUN = DONE\n')
        checklist_file.flush()
        checklist_file.close()
        #absCfgFile_list = [os.path.abspath(cfgFile) for cfgFile in cfgFile_list]

        #test must return true if nothing bad happened, false otherwise
        self.assertTrue(fwk.run(), 'error in running fwk')
        conf = ConfigObj(checklist_file_name, 
                         interpolation = 'template',
                         file_error = True)
        self.assertEquals('DONE', conf['CREATE_RUNSPACE'])
        self.assertEquals('DONE', conf['RUN_SETUP'])
        self.assertEquals('DONE', conf['RUN'])
    """

    def test_basic_serial1_permutations(self):
        print 
        cfgFile_list = []
        cfgFile_list.append('basic_serial1_laptop.conf')
        platform_filename = 'laptop.conf'
        #log_file = 'sys.stdout'
        log_file = 'log_test_basic_serial1_on_laptop.log'
        #log_file = open(os.path.abspath('log_test_basic_serial1_on_laptop.log'), 'w')
        #log_file = sys.stdout

        # create framework with config file
        true_or_false = [True, False]
        for do_create_runspace in true_or_false: 
            for create_runspace_done in true_or_false:
                for do_run_setup in true_or_false: 
                    for run_setup_done in true_or_false:
                        for do_run in true_or_false: 
                            for run_done in true_or_false:
                                param = self.Parameterization()
                                param.do_create_runspace = do_create_runspace
                                param.do_run_setup = do_run_setup
                                param.do_run = do_run
                                param.create_runspace_done = create_runspace_done
                                param.run_setup_done = run_setup_done
                                param.run_done = run_done
                                param.cfgFile_list = cfgFile_list
                                param.log_file = log_file
                                param.platform_filename = platform_filename
                                suite = unittest.TestSuite()
                                suite.addTest(ParameterizedTestCase.parametrize(test_permutations, param=param))
                                res = unittest.TextTestRunner(verbosity=2).run(suite)

    """
    def test_basic_serial1_permutations(self):
        print 
        cfgFile_list = []
        cfgFile_list.append('basic_serial1_laptop.conf')
        platform_filename = 'laptop.conf'
        log_file = 'sys.stdout'
        #log_file = 'log_test_basic_serial1_on_laptop.log'
        #log_file = open(os.path.abspath('log_test_basic_serial1_on_laptop.log'), 'w')
        #log_file = sys.stdout

        # create framework with config file
        true_or_false = [True, False]
        for do_create_runspace in true_or_false: 
            for create_runspace_done in true_or_false:
                for do_run_setup in true_or_false: 
                    for run_setup_done in true_or_false:
                        for do_run in true_or_false: 
                            for run_done in true_or_false:
                                print '------------------------------------------------------------------------------------'
                                print 'Parameterization for this test'
                                print 'DO_CREATE_RUNSPACE = %s DO_RUN_SETUP = %s DO_RUN = %s' % \
                                        (do_create_runspace, do_run_setup, do_run)
                                print 'CREATE_RUNSPACE_DONE = %s RUN_SETUP_DONE = %s RUN_DONE = %s' % \
                                        (create_runspace_done, run_setup_done, run_done)
                                print '------------------------------------------------------------------------------------'

                                #log_file = open(os.path.abspath('log_test_basic_serial1_on_laptop.log'), 'w')
                                fwk = Framework(do_create_runspace, 
                                                do_run_setup, 
                                                do_run, 
                                                cfgFile_list, 
                                                log_file, 
                                                platform_filename)
                                checklist_file_name = os.path.join(fwk.sim_root, 'checklist.conf')
                                checklist_file = open(checklist_file_name, 'w')
                                if create_runspace_done:
                                    checklist_file.write('CREATE_RUNSPACE = DONE\n')
                                else:
                                    checklist_file.write('CREATE_RUNSPACE = NOT_DONE\n')
                                if run_setup_done:
                                    checklist_file.write('RUN_SETUP = DONE\n')
                                else:
                                    checklist_file.write('RUN_SETUP = NOT_DONE\n')
                                if run_done:
                                    checklist_file.write('RUN = DONE\n')
                                else:
                                    checklist_file.write('RUN = NOT_DONE\n')
                                checklist_file.flush()
                                checklist_file.close()

                                #test must return true if nothing bad happened, false otherwise
                                self.assertTrue(fwk.run(), 'error in running fwk')

                                # set correct result of CREATE_RUNSPACE parameterization
                                if do_create_runspace or create_runspace_done:
                                    self.create_runspace_result = 'DONE'
                                else:
                                    self.create_runspace_result = 'NOT_DONE'

                                # set correct result of RUN_SETUP parameterization
                                if do_run_setup and self.create_runspace_result == 'DONE':
                                    self.run_setup_result = 'DONE'
                                else:
                                    self.run_setup_result = 'NOT_DONE'
                                    
                                # set correct result of RUN parameterization
                                if do_run and self.run_setup_result == 'DONE':
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
                                #for attr in dir(fwk):
                                #    print 'fwk.%s = %s' % (attr, getattr(fwk,attr))
                                #print '------------------------------------------------------------------------------------'
    """

if __name__ == "__main__":
    print "Starting IPS"
    sys.stdout.flush()
    unittest.main()
