#from processing import Queue
import sys
import socket
import getopt
import os
import traceback
import time
import unittest

sys.path.append('../..')

from ips import Framework

"""
    This will be the test harness for the various comprehensive tests.
    Need to do:
    * develop a way to set up different test scenarios (input files and expected results) along with descriptions
"""

class testIPS(unittest.TestCase):
    def printUsageMessage(self):
        print 'Usage: ips [--create-runspace | --run-setup | --run]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'

    def test_basic_serial1(self):
        cfgFile_list = []
        cfgFile_list.append('basic_serial1_laptop.conf')
        platform_filename = 'laptop.conf'
        log_file = 'log_test_basic_serial1_on_laptop.log'

        # create framework with config file
        fwk = Framework(True, False, False, cfgFile_list, log_file, platform_filename)
        #absCfgFile_list = [os.path.abspath(cfgFile) for cfgFile in cfgFile_list]

        #test must return true if nothing bad happened, false otherwise
        self.assertTrue(fwk.run(), 'error in running fwk')
        return 0

    """
    def test_basic_concurrent1(self):
        cfgFile_list = []
        #cfgFile_list.append('basic_concurrent1.conf')
        cfgFile_list.append('basic_serial1.conf')
        platform_filename = 'iter.conf'
        #log_file = 'test_basic_concurrent1_on_workstation.log'
        log_file = 'test_basic_serial1_on_workstation.log'

        # create framework with config file
        fwk = Framework(True, True, True, cfgFile_list, log_file, platform_filename)
        #absCfgFile_list = [os.path.abspath(cfgFile) for cfgFile in cfgFile_list]

        #test must return true if nothing bad happened, false otherwise
        self.assertTrue(fwk.run(), 'error in running fwk')
        return 0
    """

if __name__ == "__main__":
    print "Starting IPS"
    sys.stdout.flush()
    unittest.main()
