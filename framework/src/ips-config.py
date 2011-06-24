#! /usr/bin/env python

from configobj import ConfigObj
import sys
import os.path
import getopt

def printUsageMessage():
    print "Usage: ips-config --config=CONFIG_FILE_NAME --var=CONFIG_VARIABLE"

def main(argv=None):

    cfgFile = ''
    config_key=''
    # parse command line arguments
    if argv is None:
        argv = sys.argv
        try:
            opts, args = getopt.gnu_getopt(argv[1:], '', ["config=", "var="])
        except getopt.error, msg:
            print 'Invalid command line arguments', msg
            printUsageMessage()
            return 1
    for arg, value in opts:
        if (arg == '--config'):
            cfgFile = value
        elif (arg == '--var'):
            config_key = value
    if (cfgFile == '' or config_key == ''):
        printUsageMessage()
        return 1

    # create framework with config file
    absCfgFile = os.path.abspath(cfgFile)
    try:
        conf = ConfigObj(absCfgFile, interpolation='template', file_error=True)
    except SyntaxError, (ex):
        print ' Error parsing config file: ', str(ex)
        sys.exit(1)
    except IOError, (ex):
        print 'Error opening config file: ', str(ex)
        sys.exit(1)
    try:
        val = conf[config_key]
    except KeyError:
        print 'Error: no variable %s in config file %s' %(config_key, absCfgFile)
    else:
        print val
    return 0

# ----- end main -----

if __name__ == "__main__":
    sys.exit(main())
