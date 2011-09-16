import sys
import os
import subprocess
import getopt
import shutil
import string
import ipsutil
import time
from component import Component

class RunspaceInit_Component(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)


# ------------------------------------------------------------------------------
#
# init function
#
# RunspaceInit_Component init function creates base directory, copies IPS and 
# FacetsComposer input files.
#
# ------------------------------------------------------------------------------

    def init(self, timeStamp):

        print 'RunspaceInit_Component.init() called'

        services = self.services

        # get the simRootDir
        simRootDir = services.get_config_param('SIM_ROOT')
        #print 'simRootDir = ', simRootDir

        # get the configuration files and platform file
        config_files = services.fwk.config_file_list
#       print 'config_files[0]: ' + config_files[0]
#       print 'os.path.abspath(config_files[0]): ' + os.path.abspath(config_files[0])
#       print 'os.path.basename(config_files[0]): ' + os.path.basename(config_files[0])
        platform_file = services.fwk.platform_file_name
#       print 'platform_file: ' + platform_file
#       print 'os.path.abspath(platform_file): ' + os.path.abspath(platform_file)
#       print 'os.path.basename(platform_file): ' + os.path.basename(platform_file)
#
#       (head,tail) = os.path.split(os.path.abspath(config_files[0]))
#       print 'head ', head
#       print 'tail ', tail

        # uncomment when implemented
        # fc_files = services.fwk.facets_composer_files

        # copy these to the SIM_ROOT
        (head,tail) = os.path.split(os.path.abspath(config_files[0]))
#       print 'head ', head
#       print 'tail ', tail
        ipsutil.copyFiles(head, config_files, simRootDir)
        (head, tail) = os.path.split(os.path.abspath(platform_file))
#       print 'head ', head
#       print 'tail ', tail
        ipsutil.copyFiles(head, platform_file, simRootDir) 
        # uncomment when implemented
        #ipsutil.copyFiles(os.path.dirname(self.fc_files),
        #                  os.path.basename(self.fc_files), simRootDir) 

        # Get component-specific configuration parameters. Note: Not all of these are
        # used in 'init' but if any are missing we get an exception now instead of
        # later
        """
        try:
            NPROC = self.NPROC
            print 'NPROC = ', NPROC
            BIN_PATH = self.BIN_PATH
            print 'BIN_PATH = ', BIN_PATH
            INPUT_FILES = self.INPUT_FILES
            print 'INPUT_FILES = ', INPUT_FILES
            OUTPUT_FILES = self.OUTPUT_FILES
            print 'OUTPUT_FILES = ', OUTPUT_FILES
            RESTART_FILES = self.RESTART_FILES
            print 'RESTART_FILES = ', RESTART_FILES

        except:
            print 'RunspaceInit_Component init: error getting config parameters'
            services.error('RunspaceInit_Component: error getting config parameters')
            raise Exception, 'RunspaceInit_Component: error getting config parameters'

        # Get input files  
        try:
          services.stage_input_files(INPUT_FILES)
        except Exception, e:
          print 'Error in call to stageInputFiles()' , e
          services.error('Error in call to stageInputFiles()')
          raise Exception, 'Error in call to stageInputFiles()'
        """

        return

# ------------------------------------------------------------------------------
#
# parse function
#
# does nothing
#
# ------------------------------------------------------------------------------

    def validate(self, timestamp=0):
        print 'RunspaceInit_Component.parse() called'
        return

# ------------------------------------------------------------------------------
#
# step function
#
# copies individual subcomponent input files into working subdirectories
#
# ------------------------------------------------------------------------------

    def step(self, timestamp=0):

        print 'RunspaceInit_Component.step() called'

        services = self.services

# ------------------------------------------------------------------------------
#
# checkpoint function
#
# does nothing
#
# ------------------------------------------------------------------------------

    def checkpoint(self, timestamp=0.0):

        print 'RunspaceInit_Component.checkpoint() called'

        # save restart files
        # services = self.services
        # services.save_restart_files(timestamp, self.RESTART_FILES)

        return

# ------------------------------------------------------------------------------
#
# finalize function
#
# does nothing for now
#
# ------------------------------------------------------------------------------



    def finalize(self, timestamp=0.0):
        print 'RunspaceInit_Component.finalize() called'

        # zip up all of the needed files for debugging later

        return
