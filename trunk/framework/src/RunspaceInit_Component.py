import sys
import os
import subprocess
import getopt
import shutil
import string
import ipsutil
import time
import zipfile
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
        self.simRootDir = services.get_config_param('SIM_ROOT')

        try:
            os.chdir(self.simRootDir)
        except OSError, (errno, strerror):
            self.services.debug('Working directory %s does not exist - will attempt creation',
                                self.simRootDir)
            try:
                os.makedirs(self.simRootDir)
            except OSError, (errno, strerror):
                self.services.exception('Error creating directory %s : %s' ,
                                        workdir, strerror)
                #pytau.stop(timer)
                raise
        os.chdir(self.simRootDir)

        # get the configuration files and platform file
        self.config_files = services.fwk.config_file_list
        self.platform_file = services.fwk.platform_file_name

        # uncomment when implemented
        # self.fc_files = services.fwk.facets_composer_files

        # copy these to the SIM_ROOT
        (head,tail) = os.path.split(os.path.abspath(self.config_files[0]))
        ipsutil.copyFiles(head, self.config_files, self.simRootDir)
        (head, tail) = os.path.split(os.path.abspath(self.platform_file))
        ipsutil.copyFiles(head, self.platform_file, self.simRootDir) 
        # uncomment when implemented
        #(head, tail) = os.path.split(os.path.abspath(self.fc_files))
        #ipsutil.copyFiles(os.path.dirname(self.fc_files),
        #                  os.path.basename(self.fc_files), simRootDir) 

        return

# ------------------------------------------------------------------------------
#
# parse function
#
# does nothing
#
# ------------------------------------------------------------------------------

    def validate(self, timestamp=0):
        print 'RunspaceInit_Component.validate() called'
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

        sim_comps = services.fwk.config_manager.get_component_map()
        registry = services.fwk.comp_registry

        for sim_name, comp_list in sim_comps.items():
            for comp_id in comp_list:
                comp_ref = registry.getEntry(comp_id).component_ref
                comp_conf = registry.getEntry(comp_id).component_ref.config
                full_comp_id = '_'.join([comp_conf['CLASS'], comp_conf['SUB_CLASS'],
                                                  comp_conf['NAME'],
                                                  str(comp_id.get_seq_num())])
                workdir = os.path.join(self.simRootDir, 'work', full_comp_id)

                try:
                    os.makedirs(workdir)
                except OSError, (errno, strerror):
                    if (errno != 17):
                        self.services.exception('Error creating directory %s : %s' ,
                                                workdir, strerror)
                        #pytau.stop(timer)
                        raise

            workdir = services.get_working_dir()

            try:
                os.makedirs(workdir)
            except OSError, (errno, strerror):
                if (errno != 17):
                    self.services.exception('Error creating directory %s : %s' ,
                                            workdir, strerror)
                    #pytau.stop(timer)
                    raise

        return


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

        services = self.services 

        os.chdir(self.simRootDir)

        # zip up all of the needed files for debugging later
        basename = os.path.basename(self.simRootDir)
        basename = ''.join([basename, '.zip'])
        debug_zip_file = zipfile.ZipFile(basename,'w')
        debug_zip_file.write(self.platform_file)
        for file in self.config_files:
            debug_zip_file.write(file)

        return
