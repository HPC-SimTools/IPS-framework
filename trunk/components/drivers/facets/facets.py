#! /usr/bin/env python

# version 0.1 10/25/2010 (Batchelor)

# This version will either do a merge of a partial plasma state in the 'step' function so that 
# The component can be used concurrently without overwriting other components plasma state
# inputs or it can do an update of the full plasma state in the 'step' function.  This is 
# controlled by the parameter STATE_WRITE_MODE = full/partial in the facets_epa section of the
# IPS config file.  The default (i.e. STATE_WRITE_MODE absent) is merge partial state
#
# In this version the python component copies the input eqdsk file to
# current_eqdsk_file and copies the input state file to the generic name = "input_state_file" 
# The paths to the input plasma state file and input eqdsk files should be specified as input 
# files in the simulation config file.  Also config variables "INPUT_PLASMA_STATE_FILE"
# and "INPUT_EQDSK_FILE"  should be defined  with the names of these input files.

# ------------------------------------------------------------------------------
#
# EPA component script for FACETS EPA
#
#!    The fortran init executable "facets_epa_ps_file_init.f90" requires 3 commandline arguments: 
#!    1) current state file
#!    2) current eqdsk file
#!    3) timeStamp = initial time
#
# ------------------------------------------------------------------------------

import sys
import os
import subprocess
import getopt
import shutil
import string
from component import Component

class facets(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)

# ------------------------------------------------------------------------------
#
# init function
#
# facets_epa init function allocates plasma profiles and initializes rf sources
#
# ------------------------------------------------------------------------------

    def init(self, timeStamp):
        print 'facets_epa.init() called'

        services = self.services

        # Get global configuration parameters
        #try:
#            cur_state_file = services.get_config_param('CURRENT_STATE')
#            cur_eqdsk_file = services.get_config_param('CURRENT_EQDSK')
#
#        except:
#            print 'facets_epa: error in getting config parameters'
#            services.error('facets_epa: error in getting config parameters')
#            raise Exception, 'facets_epa: error in getting config parameters'

        
        # Access physics code binaries
        fg_bin_root = self.services.get_config_param('FG_BIN_ROOT')
        self.services.info("Got FG_BIN_ROOT.")
        facets_bin_root = self.services.get_config_param('FACETS_BIN_ROOT')
        self.services.info("Got FACETS_BIN_ROOT.")
        
        # Build a path to fluxgrid
        fluxgrid_bin = os.path.join(fg_bin_root, 'fluxgrid')
        self.services.info("Built a path to fluxgrid .")
        
        # Move files for inputs to work directory
        self.services.stage_input_files(self.INPUT_FILES)
        self.services.info("Moved inputs to working directory for FACETS.")
        
        # Gets working directory
        work_dir = self.services.get_working_dir()
        self.services.info("Got working directory for FACETS.")
        
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
            print 'facets_epa init: error getting component-specific config parameters'
            services.error('facets_epa: error getting component-specific\
            config parameters')
            raise Exception, 'facets_epa: error getting facets_epa-specific\
            config parameters'
     
        # Get input files  
        try:
          services.stage_input_files(INPUT_FILES)
        except Exception, e:
          print 'Error in call to stageInputFiles()' , e
          services.error('Error in call to stageInputFiles()')
          raise Exception, 'Error in call to stageInputFiles()'
          
        # Copy plasma state files over to working directory
        if "PLASMA_STATE"  in self.__dict__.keys():
            input_state_file = self.INPUT_STATE_FILE
            try:
              services.stage_plasma_state()
            except Exception, e:
              print 'Error in call to stage_plasma_state()' , e
              #services.error('Error in call to stage_plasma_state()')
              #raise Exception, 'Error in call to stage_plasma_state()'
            
            # Move input_state_file to generic name "input_state_file"
            try:
                subprocess.call(['cp', input_state_file, cur_state_file ])
            except Exception, e:
              print 'Error in renaming input_state_file' , e
              services.error('Error in renaming input_state_file')
              raise Exception, 'Error in renaming input_state_file'

            try:
              subprocess.call(['cp', input_state_file, "input_state_file" ])
            except Exception, e:
              print 'Error in renaming input_state_file' , e
              services.error('Error in renaming input_state_file')
              raise Exception, 'Error in renaming input_state_file'
            
        # If we have an eqdsk file, need to run fluxgrid to get the magnetic geometries
        shot_label=""
        if "INPUT_EQDSK_FILE" in self.__dict__.keys():
            input_eqdsk_file = self.INPUT_EQDSK_FILE
            shot_label=input_eqdsk_file[1:]
            # This is our convention that must be followed
            fluxgrid_input_file="fg_"+input_eqdsk_file+".in"
            try:
                subprocess.call([fluxgrid_bin, fluxgrid_input_file ])
            except Exception, e:
                print 'Error in running fuxgrid' , e
                services.error('Error in running fuxgrid')
                raise Exception, 'Error in running fuxgrid'
            
        # If we have an iterdb file, need to get the sources
        if "ITERDB_FILE" in self.__dict__.keys():
            iterdb_file=self.ITERDB_FILE
            try:
                getiter_bin = os.path.join(facets_bin_root, 'getIterDbData.py')
                magGeom=" -m fgMagGeom_"+input_eqdsk_file+".pre"

                # Get the beam sources
                options=" -f s_d,qbeame,qbeami -r sdens_e,senrg_e,senrg_H2p1 -c 1e-19,0.00062414,0.00062414"
                outputopt=" -o idbSource_"+shot_label+".pre "
                fullcmd=getiter_bin+options+magGeom+outputopt+iterdb_file
                print "Full command to iterdb python script is: ", fullcmd, "\n"
                subprocess.call(fullcmd.split())

                # Get the Ohmic sources
                options=" -f s_d,qohmic,qbeami -r sdens_e,senrg_e,senrg_H2p1 -c 0.0,0.00062414,0.0"
                outputopt=" -o idbOhmicSource_"+shot_label+".pre "
                fullcmd=getiter_bin+options+magGeom+outputopt+self.ITERDB_FILE
                print "Full command to iterdb python script is: ", fullcmd, "\n"
                subprocess.call(fullcmd.split())

                # Get the Radiation sources
                options=" -f s_d,qrad,qbeami -r sdens_e,senrg_e,senrg_H2p1 -c 0.0,0.00062414,0.0 "
                outputopt=" -o idbRadSource_"+shot_label+".pre "
                fullcmd=getiter_bin+options+magGeom+outputopt+self.ITERDB_FILE
                print "Full command to iterdb python script is: ", fullcmd, "\n"
                subprocess.call(fullcmd.split())

            except Exception, e:
                print 'Error in running getIterDbData.py' , 
                services.error('Error in running getIterDbData.py')
                raise Exception, 'Error in running getIterDbData.py'

        # If we have a fit file, then need to set the profiles
        if "FIT_FILES" in self.__dict__.keys():
            try:
                te_file=""; ti_file=""; ne_file=""
                for ff in self.FIT_FILES.split():
                  if "_ne" in ff: ne_file=ff
                  if "_te" in ff: te_file=ff
                  if "_ti" in ff: ti_file=ff

                getiter_bin = os.path.join(facets_bin_root, 'readPsiFit.py')
                magGeom=" -m fgMagGeom_"+input_eqdsk_file+".pre"
                # Get the density
                if ne_file:
                  options=" -r density_electron -c 1e20 "
                  outputopt=" -o psiFitDensityElectron_"+shot_label+".pre "
                  fullcmd=getiter_bin+options+magGeom+outputopt+ne_file
                  print "Full command to readpsifit python script is: ", fullcmd, "\n"
                  subprocess.call(fullcmd.split())
                
                # Set up the electron temperature
                if te_file:
                  options=" -r temperature_electron -c 1e3 "
                  outputopt=" -o psiFitTemperatureElectron_"+shot_label+".pre "
                  fullcmd=getiter_bin+options+magGeom+outputopt+te_file
                  print "Full command to readpsifit python script is: ", fullcmd, "\n"
                  subprocess.call(fullcmd.split())

                # Set up the ion temperature
                if ti_file:
                  options=" -r temperature_H2p1 -c 1e3 "
                  outputopt=" -o psiFitTemperatureH2p1_"+shot_label+".pre "
                  fullcmd=getiter_bin+options+magGeom+outputopt+ti_file
                  print "Full command to readpsifit python script is: ", fullcmd, "\n"
                  subprocess.call(fullcmd.split())

            except Exception, e:
                print 'Error in running readPsiFit.py' , 
                services.error('Error in running readPsiFit.py')
                raise Exception, 'Error in running readPsiFit.py'

        # Update plasma state files in plasma_state work directory
        if "PLASMA_STATE"  in self.__dict__.keys():
              try:
                services.update_plasma_state()
              except Exception, e:
                print 'Error in call to update_plasma_state()', e
                services.error('Error in call to update_plasma_state()')
                raise Exception, 'Error in call to update_plasma_state()'

        #Now assemble the quite large facets input file
        try:
             txpp_bin = os.path.join(facets_bin_root, 'txpp.py')
             print "Full command to txpp python script is: ", txpp_bin + " " + self.PRE_FILE, "\n"
             subprocess.call([txpp_bin,self.PRE_FILE])
        except Exception, e:
          print 'Error in running preprocessor', e
          services.error('Error in running preprocessor')
          raise Exception, 'Error in running preprocessor'

# ------------------------------------------------------------------------------
#
# RESTART function
# Gets restart files from restart directory
# Loads the global configuration parameters from the config file
#
# ------------------------------------------------------------------------------
        
    def restart(self, timeStamp):
      print 'facets_epa_ps_init.restart() called'

      services = self.services
      workdir = services.get_working_dir()

    # Get restart files listed in config file.        
      try:
            restart_root = services.get_config_param('RESTART_ROOT')
            restart_time = services.get_config_param('RESTART_TIME')
            services.get_restart_files(restart_root, restart_time, self.RESTART_FILES)
      except Exception, e:
            print 'Error in call to get_restart_files()' , e
            self.services.error('facets_epa_ps_init: error in call to get_restart_files()')
            raise Exception, 'facets_epa_ps_init: error in call to get_restart_files()'

    # Get global configuration parameters
      try:
            self.plasma_state_file = services.get_config_param('CURRENT_STATE')
            self.eqdsk_file = services.get_config_param('CURRENT_EQDSK')
            self.next_state_file = self.services.get_config_param('NEXT_STATE')
      except:
            print 'facets_epa_ps_init restart: error in getting config parameters'
            self.services.error('error in getting config parameters')
            raise Exception, 'error in getting config parameters'

      return 0

# ------------------------------------------------------------------------------
#
# PARSE function
#
# ------------------------------------------------------------------------------

    def validate(self, timeStamp):
        print 'facets_epa.validate() called'

        return 0

# ------------------------------------------------------------------------------
#
# STEP function
#
# ------------------------------------------------------------------------------

    def step(self, timeStamp):
        print 'facets_epa.step() called'

        if (self.services == None) :
            services.error('Error in facets_epa step (): No self.services')
            raise Exception('Error in facets_epa step (): No self.services')
        services = self.services

        try:
            facets_bin_root = self.services.get_config_param('FACETS_BIN_ROOT')
            facets_bin = os.path.join(facets_bin_root, 'facetsst')
            in_file=self.PRE_FILE.replace(".pre",".in")
            fullcmd=facets_bin+" -i "+in_file
            work_dir = services.get_working_dir()
            task_id = self.services.launch_task(self.NPROC, work_dir, fullcmd,
                                     logfile='facets_step.log')
        except Exception, e:
            msg='Error executing facets_epa_bin: '+str(e)
            services.error(msg)
            raise Exception(msg)


        try:
            retval = self.services.wait_task(task_id)
        except :
            self.services.exception("Error invoking facets_bin ")
            raise
        if (retval != 0):
            self.services.error('%s failed to execute properly', facets_bin)
            raise Exception

    # Archive output files
        try:
          services.stage_output_files(timeStamp, self.OUTPUT_FILES)
        except Exception, e:
          print 'Error in call to stage_output_files()', e
          self.services.error('Error in call to stage_output_files()')
          raise Exception, 'Error in call to stage_output_files()'
          
        return 0

# ------------------------------------------------------------------------------
#
# checkpoint function
# Saves plasma state files to restart directory
#
# ------------------------------------------------------------------------------

    def checkpoint(self, timestamp=0.0):
            print 'facets_epa.checkpoint() called'
            services = self.services
            services.save_restart_files(timestamp, self.RESTART_FILES)

            return 0

# ------------------------------------------------------------------------------
#
# finalize function
#
# Does nothing
# ------------------------------------------------------------------------------



    def finalize(self, timestamp=0.0):
        print 'facets_epa finalize() called'
