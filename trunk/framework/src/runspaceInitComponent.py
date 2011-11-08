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

class runspaceInitComponent(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)


# ------------------------------------------------------------------------------
#
# init function
#
# runspaceInitComponent init function creates base directory, copies IPS and 
# FacetsComposer input files.
#
# ------------------------------------------------------------------------------

    def init(self, timeStamp):

        print 'runspaceInitComponent.init() called'

        services = self.services

        # get the simRootDir
        self.simRootDir = services.get_config_param('SIM_ROOT')
        if not self.simRootDir.startswith("/"):
          self.simRootDir=os.path.abspath(self.simRootDir)

        # try making the simulation root directory
        try: 
            os.makedirs(self.simRootDir)
        except OSError, (errno, strerror):
            if (errno != 17):
                self.services.exception('Error creating directory %s : %s' ,
                        workdir, strerror)

        self.config_files = services.fwk.config_file_list
        self.platform_file = services.fwk.platform_file_name
        self.main_log_file = services.get_config_param('LOG_FILE')
#       print 'log_file = ', self.main_log_file

        # uncomment when implemented
        # self.fc_files = services.fwk.facets_composer_files

        # copy these to the SIM_ROOT
        (head,tail) = os.path.split(os.path.abspath(self.config_files[0]))
#       print 'head ', head
#       print 'tail ', tail
        ipsutil.copyFiles(head, self.config_files, self.simRootDir)
        (head, tail) = os.path.split(os.path.abspath(self.platform_file))
#       print 'head ', head
#       print 'tail ', tail
        ipsutil.copyFiles(head, self.platform_file, self.simRootDir) 

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
        print 'runspaceInitComponent.validate() called'
        return

# ------------------------------------------------------------------------------
#
# step function
#
# copies individual subcomponent input files into working subdirectories
#
# ------------------------------------------------------------------------------

    def step(self, timestamp=0):

        print 'runspaceInitComponent.step() called'

        services = self.services

        sim_comps = services.fwk.config_manager.get_component_map()
        registry = services.fwk.comp_registry

        simulation_setup = os.path.join(self.simRootDir, 'simulation_setup')

        # make the simulation_setup directory for scripts
        try: 
            os.makedirs(simulation_setup)
        except OSError, (errno, strerror):
            if (errno != 17):
                self.services.exception('Error creating directory %s : %s' ,
                        workdir, strerror)

        # for each simulation component
        for sim_name, comp_list in sim_comps.items():
            # for each component_id in the list of components
            for comp_id in comp_list:
                # build the work directory name
                comp_ref = registry.getEntry(comp_id).component_ref
                comp_conf = registry.getEntry(comp_id).component_ref.config
                full_comp_id = '_'.join([comp_conf['CLASS'], comp_conf['SUB_CLASS'],
                                                  comp_conf['NAME'],
                                                  str(comp_id.get_seq_num())])

                # compose the workdir name
                workdir = os.path.join(self.simRootDir, 'work', full_comp_id)

#               print 'workdir = ', workdir

                # make the working directory
                try:
                    os.makedirs(workdir)
                except OSError, (errno, strerror):
                    if (errno != 17):
                        self.services.exception('Error creating directory %s : %s' ,
                                                workdir, strerror)
                        #pytau.stop(timer)
                        raise
                
                # copy the input files into the working directory
                ipsutil.copyFiles(os.path.abspath(comp_conf['INPUT_DIR']),
                                  os.path.basename(comp_conf['INPUT_FILES']),
                                  workdir)

                # This is a bit tricky because we want to look either in the same 
                # place as the input files or the data_tree root
                if comp_conf.has_key('DATA_FILES'):
                  filesCopied=False
                  if comp_conf.has_key('DATA_TREE_ROOT'):
                    dtrdir=os.path.abspath(comp_conf['DATA_TREE_ROOT'])
                    if os.path.exists(os.path.join(dtrdir,comp_conf['DATA_FILES'][0])):
                      ipsutil.copyFiles(dtrdir,os.path.basename(comp_conf['DATA_FILES']),
                                        workdir)
                      filesCopied=True
                  if not filesCopied:
                     ipsutil.copyFiles(os.path.abspath(comp_conf['INPUT_DIR']),
                                       os.path.basename(comp_conf['DATA_FILES']),
                                       workdir)

                # copy the component's script to the simulation_setup directory
                if os.path.abspath(comp_conf['SCRIPT'])==comp_conf['SCRIPT']:
                  ipsutil.copyFiles(os.path.dirname(comp_conf['SCRIPT']),
                                    [os.path.basename(comp_conf['SCRIPT'])],
                                    simulation_setup)
                else:
                  ipsutil.copyFiles(comp_conf['BIN_DIR'],
                                    [os.path.basename(comp_conf['SCRIPT'])],
                                    simulation_setup)

            # get the working directory from the runspaceInitComponent
            workdir = services.get_working_dir()

            # create the working directory for this component
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

        print 'runspaceInitComponent.checkpoint() called'

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
        print 'runspaceInitComponent.finalize() called'

        services = self.services 

        # zip up all of the needed files for debugging later
        rootdir=os.path.abspath(os.path.join(self.simRootDir,'..'))
        basename = os.path.basename(self.simRootDir)
        basename = ''.join([basename, '.zip'])
        containerName = os.path.join(rootdir,basename)
        debug_zip_file = zipfile.ZipFile(containerName,'w')
        debug_zip_file.write(self.platform_file)
        debug_zip_file.write('resource_usage')
        (head, tail) = os.path.split(self.main_log_file)
        debug_zip_file.write(tail)
        for file in self.config_files:
            debug_zip_file.write(file)

        return
