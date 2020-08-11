# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
import getopt
import os
import unittest
from ips import Framework


def printUsageMessage():
    print("Usage: ips [--create-runspace | --run-setup | --run]+ --simulation=SIM_FILE_NAME "
          "--platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]")


class testIPS(unittest.TestCase):
    def test_main(self, argv=None):
        cfgFile_list = []
        platform_filename = ''
        log_file = sys.stdout
        # parse command line arguments
        if argv is None:
            argv = sys.argv
            first_arg = 1
        else:
            first_arg = 0

        try:
            opts, args = getopt.gnu_getopt(argv[first_arg:], '',
                                           ["create-runspace", "run-setup", "run",
                                            "simulation=", "platform=", "log=",
                                            "nodes=", "ppn=",
                                            "debug", "verbose", "ftb"])
        except getopt.error as msg:
            self.fail('Invalid command line arguments' + msg)
            # print 'Invalid command line arguments', msg
            # printUsageMessage()
            # return 1
        for arg, value in opts:
            if (arg == '--config'):
                cfgFile_list.append(value)
            elif (arg == '--log'):
                log_file_name = value
                try:
                    log_file = open(os.path.abspath(log_file_name), 'w')
                except Exception as e:
                    self.fail('Error writing to log file ' + log_file_name + '\n' + str(e))
                    # print 'Error writing to log file ' , log_file_name
                    # print str(e)
                    # raise
            elif (arg == '--platform'):
                platform_filename = value
        self.assertFalse(len(cfgFile_list) == 0, 'Empty cfgFile_list')
        self.assertFalse(platform_filename == '', 'No platform config file listed')

        # create framework with config file
        fwk = Framework(True, True, True, cfgFile_list, log_file, platform_filename)

        # test must return true if nothing bad happened, false otherwise.
        self.assertTrue(fwk.run(), 'error in running fwk')
        return 0

# ----- end main -----


if __name__ == "__main__":
    print("Starting IPS")
    sys.stdout.flush()
    args = '--simulation=sim.conf --simulation=sim2.conf --platform=jaguar.conf'
    argv = args.split(' ')
    sys.exit(unittest.main(argv))
