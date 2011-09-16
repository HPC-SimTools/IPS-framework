#!/usr/bin/env python
from makoInputBase import *
from exposedVars import *
import optparse
import os, shutil

def main():
    parser = optparse.OptionParser(usage="%prog -i <inputFile> [-g <guiFile>] [-n <newDir>] ")
    parser.add_option('-i', '--input', dest='inputFile',
                      help='Name of mako template file.',
                      default='')
    parser.add_option('-g', '--gui', dest='guiFile',
                      help='Name of gui file which gives the forms',
                      default='')
    parser.add_option('-n', '--newdir', dest='newDir',
                      help='New directory in which to put the files',
                      default='')

    options, args = parser.parse_args()

    # Too many arguments
#    print options
#    print args
#    print len(args)
    if len(args) > 10:
      parser.print_usage()
      return
#    elif len(args) == 0:
#      parser.print_usage()
#      return
    else:
      if options.inputFile == '':
        print "Must specify input file"
        return
      else:
        inputFile=options.inputFile

      if options.guiFile == '':
        doGui=False
      else:
        doGui=True
        guiFile=options.guiFile

      if options.newDir == '':
        doNewDir=False
      else:
        doNewDir=True
        newDir=options.newDir

    #================================================================
    #  Options done.  Onto the show
    #================================================================
    fileName=inputFile

    # This is the "Create Runspace" part of the script
    # IPS/simyan does this much better
    if doNewDir:
      os.mkdir(newDir)
      shutil.copy(inputFile,newDir)
      if doGui: shutil.copy(guiFile,newDir)
      if os.path.sep in inputFile:
        fileName=os.path.join(newDir,os.path.basename(inputFile))

    # This is the workflow to do if there is a gui file
    if doGui:
      attribs=ctkguiGetAttribs(guiFile)
      newattribs=getValuesInteractively(attribs)
      replaceCurrentValues(fileName,newattribs)
      renderTemplate(fileName,newattribs)
    else:
      attribs=ctkguiGetAttribs(guiFile)

if __name__ == "__main__":
        main()
