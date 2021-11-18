# -------------------------------------------------------------------------------
#  Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

"""
This example component is ../../components/rf/toric/src/rf_ic_toric_mcmd.py
It has been used as the basis for the skeleton component, and been documented to help new component writers.

MCMD version of TORIC component.  Slightly adapted from rf_ic_toric.py

"""

# ----------------------------------------------------------------------------
#  import modules
# ----------------------------------------------------------------------------

import os
import subprocess  # not used in skeleton, but useful for launching helper scripts
from ipsframework import Component  # REQUIRED - all components inherit the IPS Component


class example(Component):  # CHANGE CLASS NAME

    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

# -----------------------------------------------------------------------------
#  init function
# -----------------------------------------------------------------------------

    def init(self, timeStamp=0):
        """
        Set up component initial state in order to do first step by copying and modifying input files in work directory.
        """
        print('example.init() called')  # CHANGE TO USE NEW CLASS NAME

        services = self.services       # it is just more convenient to not type "self." all the time

        # change to work directory for this component and return that location
        workdir = services.get_working_dir()

        # Get global configuration parameters and set internal data needed for initialization work
        try:
            self.plasma_state_file = services.get_config_param('CURRENT_STATE')
            # and what ever else is needed
        except Exception:
            # CHANGE example_comp TO COMPONENT NAME
            print('example_comp: error in getting config parameters')        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example_comp: error in getting config parameters')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example_comp: error in getting config parameters')        # CHANGE EXAMPLE TO COMPONENT NAME

        # Optional - setup component's log file
        self.example_log = os.path.join(workdir, 'log.example')        # CHANGE EXAMPLE TO COMPONENT NAME

        # Copy plasma state files over to working directory
        try:
            services.stage_state()  # automatically copies current plasma state to work dir
        except Exception as e:
            print('example: Error in call to stage_state()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to stage_state()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to stage_state()')        # CHANGE EXAMPLE TO COMPONENT NAME

        # Get input files
        try:
            services.stage_input_files(self.INPUT_FILES)  # moves config file specified input files to work dir
        except Exception as e:
            print('example: Error in call to stage_input_files()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to stage_input_files()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to stage_input_files()')        # CHANGE EXAMPLE TO COMPONENT NAME

        # run init helper executable <init_helper>
        # CHANGE init_helper TO YOUR INIT HELPER PROGRAM
        init_helper = os.path.join(self.BIN_PATH, 'init_helper')
        retcode = subprocess.call([init_helper, ])
        if (retcode != 0):
            print('example: Error in call to init_helper')        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to init_helper')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to init_helper')        # CHANGE EXAMPLE TO COMPONENT NAME

        # If your init_helper made changes to the plasma_state, update them so other components can see them.
        try:
            services.update_state()
        except Exception as e:
            print('example: Error in call to update_state()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to update_state()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to update_state()')        # CHANGE EXAMPLE TO COMPONENT NAME

        # Archive output files to output tree to save your work
        try:
            services.stage_output_files(timeStamp, self.OUTPUT_FILES)
        except Exception as e:
            print('example: Error in call to stage_output_files()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to stage_output_files()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to stage_output_files()')        # CHANGE EXAMPLE TO COMPONENT NAME

        return 0

# ------------------------------------------------------------------------------
#
# RESTART function
# Gets restart files from restart directory
# Loads the global configuration parameters from the config file
#
# ------------------------------------------------------------------------------

    def restart(self, timeStamp):
        """
        actions to restart from an IPS checkpoint
        """
        print('example.restart() called')

        services = self.services
        workdir = services.get_working_dir()

        # Get restart files listed in config file.
        try:
            restart_root = services.get_config_param('RESTART_ROOT')
            restart_time = services.get_config_param('RESTART_TIME')
            # given the root of the restart tree and a restart time, the restart files
            # for this component will be placed in the workdir
            services.get_restart_files(restart_root, restart_time, self.RESTART_FILES)
        except Exception as e:
            print('example: Error in call to get_restart_files()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to get_restart_files()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise e

        # Get global configuration parameters and set internal data
        try:
            self.plasma_state_file = services.get_config_param('CURRENT_STATE')
            self.example_log = os.path.join(workdir, 'log.example')        # CHANGE EXAMPLE TO COMPONENT NAME
            # and what ever else is needed
        except Exception:
            print('example restart: error in getting config parameters')        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in getting config parameters')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in getting config parameters')        # CHANGE EXAMPLE TO COMPONENT NAME

        return 0

# ------------------------------------------------------------------------------
#
# STEP function
#
# ------------------------------------------------------------------------------

    def step(self, timeStamp):
        """
        Perform that action that this component is designed for.

        In most cases that means running a computational model of some physical
        phenomena, along with all necessary data movement and helper programs to
        couple the data to the other components of the simulation.
        """
        print('example.step() called')              # CHANGE EXAMPLE TO COMPONENT NAME

        if (self.services is None):
            print('example: Error in step(): No self.services')        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in step(): No self.services')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in step(): No self.services')        # CHANGE EXAMPLE TO COMPONENT NAME

        services = self.services
        workdir = services.get_working_dir()

        # Copy plasma state files over to working directory
        try:
            services.stage_state()
        except Exception as e:
            print('example: Error in call to stage_state()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to stage_state()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to stage_state()')        # CHANGE EXAMPLE TO COMPONENT NAME

        # Get input files
        try:
            services.stage_input_files(self.INPUT_FILES)
        except Exception as e:
            print('example: Error in call to stage_input_files()', e)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to stage_input_files()')        # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to stage_input_files()')        # CHANGE EXAMPLE TO COMPONENT NAME

        # get the executables that will be run during step()
        prepare_input = os.path.join(self.BIN_PATH, 'prepare_example_input')         # CHANGE EXAMPLE TO COMPONENT NAME
        process_output = os.path.join(self.BIN_PATH, 'process_example_output')        # CHANGE EXAMPLE TO COMPONENT NAME
        example_bin = self.EXAMPLE_BIN        # CHANGE EXAMPLE TO COMPONENT NAME

        cur_state_file = self.plasma_state_file
        example_log = self.example_log        # CHANGE EXAMPLE TO COMPONENT NAME

        # Call EXAMPLE prepare_input to generate the input files the executable is expecting
        retcode = subprocess.call([prepare_input])
        if (retcode != 0):
            print('example: Error executing ', prepare_input)        # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('Error executing EXAMPLE prepare_input')  # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('Error executing EXAMPLE prepare_input')  # CHANGE EXAMPLE TO COMPONENT NAME

        # Launch EXAMPLE executable
        print('example processors = ', self.NPROC)      # CHANGE EXAMPLE TO COMPONENT NAME
        task_id = services.launch_task(self.NPROC, workdir, example_bin, logfile=example_log)      # CHANGE EXAMPLE TO COMPONENT NAME
        # launch_task is non-blocking, thus we need to wait for it to finish
        retcode = services.wait_task(task_id)

        # check the return code or other mechanism to determine if the execution was successful
        if (retcode != 0):
            print('example: Error executing command: ', example_bin)      # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('Error executing EXAMPLE')      # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('Error executing EXAMPLE')      # CHANGE EXAMPLE TO COMPONENT NAME

        # Call process_output
        retcode = subprocess.call([process_output])
        if (retcode != 0):
            print('Example: Error executing', process_output)       # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('Error executing EXAMPLE process_output')      # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('Error executing EXAMPLE process_output')      # CHANGE EXAMPLE TO COMPONENT NAME

        # Merge partial plasma state containing updated IC data
        try:
            partial_file = workdir + '/EXAMPLE_' + cur_state_file      # CHANGE TO LOCATION OF PARTIAL PS
            services.merge_current_state(partial_file, logfile='log.update_state')
            print('merged EXAMPLE plasma state data ', partial_file)      # CHANGE EXAMPLE TO COMPONENT NAME
        except Exception:
            print('example: Error in call to merge_current_state(', partial_file, ')')      # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to merge_current_state')      # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to merge_current_state')      # CHANGE EXAMPLE TO COMPONENT NAME

        # Archive output files
        try:
            services.stage_output_files(timeStamp, self.OUTPUT_FILES)
        except Exception as e:
            print('example: Error in call to stage_output_files()', e)      # CHANGE EXAMPLE TO COMPONENT NAME
            self.services.error('example: Error in call to stage_output_files()')      # CHANGE EXAMPLE TO COMPONENT NAME
            raise Exception('example: Error in call to stage_output_files()')      # CHANGE EXAMPLE TO COMPONENT NAME

        return 0

# ------------------------------------------------------------------------------
#
# checkpoint function
# Saves plasma state files to restart directory
#
# ------------------------------------------------------------------------------

    def checkpoint(self, timestamp=0.0):
        print('example.checkpoint() called')        # CHANGE EXAMPLE TO COMPONENT NAME
        services = self.services
        services.save_restart_files(timestamp, self.RESTART_FILES)

# ------------------------------------------------------------------------------
#
# FINALIZE function
# As of now it does nothing
#
# ------------------------------------------------------------------------------

    def finalize(self, timestamp=0.0):
        print('example.finalize() called')        # CHANGE EXAMPLE TO COMPONENT NAME
