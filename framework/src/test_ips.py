import sys
import socket
import getopt
import os
import traceback
import time
from componentRegistry import ComponentID
from ipsExceptions import BlockedMessageException
from eventService import EventService
from cca_es_spec import initialize_event_service
from ipsLogging import ipsLogger
import logging, logging.handlers
import unittest
from ips import Framework

def printUsageMessage():
    print 'Usage: ips [--config=CONFIG_FILE_NAME]+ --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME'

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
                                           ["config=", "platform=", "log="])
        except getopt.error, msg:
            self.fail('Invalid command line arguments'+ msg)
            #print 'Invalid command line arguments', msg
            #printUsageMessage()
            #return 1
        for arg, value in opts:
            if (arg == '--config'):
                cfgFile_list.append(value)
            elif (arg == '--log'):
                log_file_name = value
                try:
                    log_file = open(os.path.abspath(log_file_name), 'w')
                except Exception, e:
                    self.fail('Error writing to log file ' + log_file_name + '\n' + str(e))
                    #print 'Error writing to log file ' , log_file_name
                    #print str(e)
                    #raise
            elif (arg == '--platform'):
                platform_filename = value
        self.failIf(len(cfgFile_list) == 0, 'Empty cfgFile_list')
        self.failIf( platform_filename =='', 'No platform config file listed')


        # create framework with config file
        fwk = Framework(cfgFile_list, log_file, platform_filename)
        absCfgFile_list = [os.path.abspath(cfgFile) for cfgFile in cfgFile_list]

        # test must return true if nothing bad happened, false otherwise.
        self.assertTrue(fwk.run(), 'error in running fwk')
        return 0

# ----- end main -----

if __name__ == "__main__":
    print "Starting IPS"
    sys.stdout.flush()
    args = '--config=sim.conf --config=sim2.conf --platform=jaguar.conf'
    argv = args.split(' ')
    sys.exit(unittest.main(argv))
