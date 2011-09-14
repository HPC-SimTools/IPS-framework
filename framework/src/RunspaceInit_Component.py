import sys
import os
import subprocess
import getopt
import shutil
import string
from services import ServicesProxy
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

        # get the simRootDir, then make it
        simRootDir = services.get_config_param('SIM_ROOT')

        try:
            os.makedirs(simRootDir)
        except OSError, (errno, strerror):
            if (errno != 17):
                self.fwk.exception('Error creating Simulation directory %s : %d %s' ,
                                   simRootDir, errno, strerror)
               #pytau.stop(self.timers['_initialize_sim'])
               #stop(self.timers['_initialize_sim'])
                raise


        # get the configuration files and platform file
        config_files = services.fwk.config_file_list
        platform_file = services.fwk.platform_file_name
        # uncomment when implemented
        # fc_files = services.fwk.facets_composer_files

        # copy these to the SIM_ROOT
        ipsutil.copyFiles(os.path.dirname(conf_files,
                          os.path.basename(conf_files), simRootDir)
        ipsutil.copyFiles(os.path.dirname(self.platform_file),
                          os.path.basename(self.platform_file), simRootDir) 
        # uncomment when implemented
        #ipsutil.copyFiles(os.path.dirname(self.fc_files),
        #                  os.path.basename(self.fc_files), simRootDir) 

        # Get component-specific configuration parameters. Note: Not all of these are
        # used in 'init' but if any are missing we get an exception now instead of
        # later
        try:
            NPROC = self.NPROC
            BIN_PATH = self.BIN_PATH
            INPUT_FILES = self.INPUT_FILES
            OUTPUT_FILES = self.OUTPUT_FILES
            RESTART_FILES = self.RESTART_FILES
            BIN_PATH = self.BIN_PATH

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
