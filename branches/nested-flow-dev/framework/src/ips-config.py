#! /usr/bin/env python
#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------

from configobj import ConfigObj
import sys
import os.path
import optparse
import inspect

def getCpFilesFromIps(ipsConf):
    """
    This goes through all of the components and gets the input and data files in order to
    decide what to copy over.
    """
    allCpFiles=[]
    for component in ipsConf['PORTS']['NAMES'].split():
        compimp=ipsConf['PORTS'][component]['IMPLEMENTATION']
        if ipsConf[compimp].has_key('INPUT_FILES'):
            allCpFiles.append(ipsConf[compimp]['INPUT_FILES'])
        if ipsConf[compimp].has_key('DATA_FILES'):
            allCpFiles.append(ipsConf[compimp]['DATA_FILES'])
    return allCpFiles


def main(argv=None):
    #usagemsg="Usage: ips-config --config=CONFIG_FILE_NAME --var=CONFIG_VARIABLE"
    #parser = optparse.OptionParser(usage=usagemsg)
    parser = optparse.OptionParser()
    parser.add_option('-c', '--config', dest='cfgFile', default='',
                      help='Config file name')
    parser.add_option('-v', '--var', dest='var', default='',
                      help='Config variable with CP_FILES as special keyword')
    parser.add_option('-s', '--compset', dest='compset', default='',
                      help='Component set corresponding to a conf file')

    # parse command line arguments
    options, args = parser.parse_args()

    # Various checks
    if len(args) >= 1:
        parser.print_usage()
        return

    cfgFile = ''
    config_key=''
    compset_list=[]
    if options.cfgFile:
        cfgFile=os.path.abspath(options.cfgFile)
    else:
        print "config file required"
        return
    if options.var:
        config_key=options.var
    else:
        print "config variable required"
        return

    # Try to see if we can find the platform file
    ipsPathName=inspect.getfile(inspect.currentframe())
    ipsDir=os.path.dirname(ipsPathName)
    ipsPDir0=os.path.dirname(ipsPathName)
    ipsPDir1=os.path.dirname(ipsPDir0)
    ipsPDir2=os.path.dirname(ipsPDir1)
    # This is if we've installed it
    pconf=os.path.join('share','platform.conf')
    platform_list=[]
    if os.path.exists(os.path.join(ipsPDir1,pconf)):
        ipsShareDir=os.path.join(ipsPDir1,'share')
        platform_list=[os.path.join(ipsShareDir,'platform.conf')]
    # This is looking in the build directory.
    elif os.path.exists(os.path.join(ipsPDir2,pconf)):
        ipsShareDir=os.path.join(ipsPDir2,'share')
        platform_list=[os.path.join(ipsShareDir,'platform.conf')]

    # Try to see if we can find a component file.  Can ask for one
    compset_list=[]
    if options.compset:
        cfile='component-'+options.compset+'.conf'
        fullcfile=os.path.join(ipsShareDir,cfile)
        if os.path.exists(fullcfile):
            compset_list.append(fullcfile)
        else:
            print "Could not find: ", cfile
    else:
        if os.path.exists(os.path.join(ipsShareDir,'component-generic.conf')):
            compset_list.append(os.path.join(ipsShareDir,'component-generic.conf'))
        else:
            #print "Cannot find any component configuration files."
            #print "  Assuming that variables are defined anyway"
            pass

    # Construct list of all configuration files
    conf_list=platform_list+compset_list+[cfgFile]
    conf_tuple=tuple(conf_list)

    # Create confObj object
    try:
        conf = ConfigObj(conf_tuple, interpolation='template', file_error=True)
    except SyntaxError, (ex):
        print ' Error parsing config file: ', str(ex)
        sys.exit(1)
    except IOError, (ex):
        print 'Error opening config file: ', str(ex)
        sys.exit(1)

    # Now get data as needed
    if config_key == 'CP_FILES':
        try:
            print 'call getCpFilesFromIps'
            val = getCpFilesFromIps(conf)
        except KeyError:
            print 'Error: cannot get copy files in config file %s' %(str(conf_tuple))
            return 1
        else:
            print val
            return 0
    else:
        try:
            val = conf[config_key]
        except KeyError:
            print 'Error: no variable %s in config file %s' %(config_key, str(conf_tuple))
            return 1
        else:
            print val
            return 0

# ----- end main -----

if __name__ == "__main__":
    sys.exit(main())
