#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
#!/usr/bin/env python

import os
import sys
import optparse
import glob
import zipfile
import inspect
containerizepath = inspect.getfile(inspect.currentframe())
containerizedir = os.path.dirname(containerizepath)

import configobj

class containerize:
    def __init__(self, label, dirToContain, filelist='', overwrite=False):
        self.saveGlob = [label + '*.pre', '*.nml', 'ue*-inputfile.py', 'fg*.in', '*.ips']
        containerName = label + ".fcz"

        # Get the data which is in a configObj format
        if os.path.exists(containerName) and not overwrite:
            print "Error: " + containerName + " exists."
            return 0

        # There is only one key
        curdir = os.path.abspath(os.path.curdir)
        os.chdir(dirToContain)
        if not filelist:
            filelist = []
            for globpat in self.saveGlob:
                filelist = filelist + glob.glob(globpat)
        os.chdir(curdir)

        zip_file = zipfile.ZipFile(containerName, 'w')
        for zfile in filelist:
            print dirToContain
            print zfile
            fullzfile = os.path.join(dirToContain, zfile)
            zip_file.write(fullzfile)
        zip_file.close()


def getInputFilesFromIps(dirToContain, ipsFileName):
    curdir = os.path.abspath(os.path.curdir)
    if not os.path.exists(ipsFileName):
        os.chdir(dirToContain)
        if not os.path.exists(ipsFileName):
            print "Cannot find IPS File."
    ipsConf = configobj.ConfigObj(ipsFileName, file_error=True)
    allCpFiles = []
    for component in ipsConf['PORTS']['NAMES']:
        compimp = ipsConf['PORTS'][component]['IMPLEMENTATION']
        if ipsConf[compimp].has_key('INPUT_FILES'):
            allCpFiles.append(ipsConf[compimp]['INPUT_FILES'])
        if ipsConf[compimp].has_key('DATA_FILES'):
            allCpFiles.append(ipsConf[compimp]['DATA_FILES'])
    os.chdir(curdir)
    return allCpFiles

def filelist_callback(options, opt_str, values, parser):
    setattr(parser.values, options.dest, values.split(','))

def main():
    parser = optparse.OptionParser(usage="%prog [options] dirToContain")
    parser.add_option('-l', '--label', dest='label', default='',
                      help='label of composer name.')
    parser.add_option('-o', '--overwrite', dest='doOverWrite', action='store_false',
                      help='Overwrite the container file if it exists')
    parser.add_option('-f', '--filelist', type='string',
                      action='callback', callback=filelist_callback,
                      help='List of files to include into the container file.')
    parser.add_option('-w', '--ipswf', dest='ipsfile', default='',
                      help='IPS Workflow file')

    options, args = parser.parse_args()

    # Do some basic idiot checking
    if len(args) != 1:
        parser.print_usage()
        return
    else:
        dirToContain = args[0]
        if options.label == '':
            print "Must specify a label"
            return

    # Set a filelist if option specify
    filelist = []
    if options.filelist:
        filelist = options.filelist
    if options.ipsfile:
        filelist = getInputFilesFromIps(dirToContain, ipsfile)

    # Now do the containerization
    sw = containerize(options.label, dirToContain, filelist, options.doOverWrite)

if __name__ == "__main__":
    main()
