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

sys.path.append('..')
from frameworkpath import *
sys.path.append(fsrc)
sys.path.append('../components/drivers')
sys.path.append('../components/workers')

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
    def test_single_permutation(self):
        print
        cfgFile_list = []
        cfgFile_list.append('basic_serial1.ips')


        log_file = 'log_test_basic_serial1.log'
        param = self.Parameterization()
        param.do_create_runspace = True
        param.do_run_setup = False
        param.do_run = True
        param.create_runspace_done = False
        param.run_setup_done = False
        param.run_done = True
        param.cfgFile_list = cfgFile_list
        param.log_file = log_file
        try:
           param.platform_filename = platform_filename
        except:
           print "Getting platform file from build"
        suite = unittest.TestSuite()
        suite.addTest(ParameterizedTestCase.parametrize(test_permutations, param=param))
        res = unittest.TextTestRunner(verbosity=2).run(suite)
    """

#   """
    def test_basic_serial1_permutations(self):
        print 
        cfgFile_list = []
        cfgFile_list.append('basic_serial1.ips')


        log_file = 'log_test_basic_serial1.log'
        #log_file = open(os.path.abspath('log_test_basic_serial1_on_iter.log'), 'w')
        #log_file = 'sys.stdout'

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
                                try:
                                   param.platform_filename = platform_filename
                                except:
                                   print "Getting platform file from build"
                                suite = unittest.TestSuite()
                                suite.addTest(ParameterizedTestCase.parametrize(test_permutations, param=param))
                                res = unittest.TextTestRunner(verbosity=2).run(suite)
#   """


if __name__ == "__main__":
    print "Starting IPS"
    sys.stdout.flush()
    unittest.main()
