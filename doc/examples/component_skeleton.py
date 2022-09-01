# -------------------------------------------------------------------------------
#  Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

"""
This is a skeleton of a component.  It is intended to be used as a basis for
creating a new component from scratch.  Below you will find places to insert
your own code, and places to change the current text to reflect your component.
"""

import os
import subprocess
from Scientific.IO.NetCDF import NetCDFFile
from ipsframework import Component


class my_comp (Component):

    def __init__(self, services, config):
        super().__init__(services, config)
        print(('Created %s' % (self.__class__)))

# -----------------------------------------------------------------------------
#
# init function
#
# -----------------------------------------------------------------------------

    def init(self, timeStamp=0):
        print('toric.init() called')

        services = self.services
        workdir = services.get_working_dir()

        # Get global configuration parameters
        try:
            self.plasma_state_file = services.get_config_param('CURRENT_STATE')
            self.eqdsk_file = services.get_config_param('CURRENT_EQDSK')
            self.toric_log = os.path.join(workdir, 'log.toric')
        except Exception:
            print('rf_ic_toric_mcmd: error in getting config parameters')
            self.services.error('rf_ic_toric_mcmd: error in getting config parameters')
            raise Exception('rf_ic_toric_mcmd: error in getting config parameters')

        cur_state_file = self.plasma_state_file

        # Copy plasma state files over to working directory
        try:
            services.stage_state()
        except Exception as e:
            print('Error in call to stage_state()', e)
            self.services.error('Error in call to stage_state()')
            raise Exception('Error in call to stage_state()')

        # Get input files
        try:
            services.stage_input_files(self.INPUT_FILES)
        except Exception as e:
            print('Error in call to stage_input_files()', e)
            self.services.error('Error in call to stage_input_files()')
            raise Exception('Error in call to stage_input_files()')

        # run TORIC init
        do_input = os.path.join(self.BIN_PATH, 'do_toric_init')
        retcode = subprocess.call([do_input, cur_state_file])
        if (retcode != 0):
            print('Error in call to toric_init')
            self.services.error('Error in call to toric_init')
            raise Exception('Error in call to toric_init')

        # Update plasma state files in plasma_state work directory
        try:
            services.update_state()
        except Exception as e:
            print('Error in call to update_state()', e)
            self.services.error('Error in call to update_state()')
            raise Exception('Error in call to update_state()')

        # Archive output files
        # N.B.  do_toric_init does not produce a complete set of TORIC output
        #       files.  This causes an error in stage_output_files().  To
        #       solve this we generate a dummy set of output files here with
        #       system call 'touch'
        for file in self.OUTPUT_FILES.split():
            print('touching ', file)
            subprocess.call(['touch', file])
            # Now stage them
        try:
            services.stage_output_files(timeStamp, self.OUTPUT_FILES)
        except Exception as e:
            print('Error in call to stage_output_files()', e)
            self.services.error('Error in call to stage_output_files()')
            raise Exception('Error in call to stage_output_files()')

        return 0

# ------------------------------------------------------------------------------
#
# RESTART function
# Gets restart files from restart directory
# Loads the global configuration parameters from the config file
#
# ------------------------------------------------------------------------------

    def restart(self, timeStamp):
        print('toric.restart() called')

        services = self.services
        workdir = services.get_working_dir()

        # Get restart files listed in config file.
        try:
            restart_root = services.get_config_param('RESTART_ROOT')
            restart_time = services.get_config_param('RESTART_TIME')
            services.get_restart_files(restart_root, restart_time, self.RESTART_FILES)
        except Exception as e:
            print('Error in call to get_restart_files()', e)
            raise

        # Get global configuration parameters
        try:
            self.plasma_state_file = services.get_config_param('CURRENT_STATE')
            self.eqdsk_file = services.get_config_param('CURRENT_EQDSK')
            self.toric_log = os.path.join(workdir, 'log.toric')
        except Exception:
            print('toric restart: error in getting config parameters')
            self.services.error('error in getting config parameters')
            raise Exception('error in getting config parameters')

        return 0

# ------------------------------------------------------------------------------
#
# STEP function
#
# ------------------------------------------------------------------------------

    def step(self, timeStamp):
        """Take a step for the toric component.  Really a complete run."""
        print('toric.step() called')

        if (self.services is None):
            print('Error in toric: step (): No self.services')
            self.services.error('Error in toric: step (): No self.services')
            raise Exception('Error in toric: step (): No self.services')
        services = self.services

        # Copy plasma state files over to working directory
        try:
            services.stage_state()
        except Exception as e:
            print('Error in call to stage_state()', e)
            self.services.error('Error in call to stage_state()')
            raise Exception('Error in call to stage_state()')

        # Get input files
        try:
            services.stage_input_files(self.INPUT_FILES)
        except Exception as e:
            print('Error in call to stage_input_files()', e)
            self.services.error('Error in call to stage_input_files()')
            raise Exception('Error in call to stage_input_files()')

        prepare_input = os.path.join(self.BIN_PATH, 'prepare_toric_input')
        process_output = os.path.join(self.BIN_PATH, 'process_toric_output_mcmd')
        zero_RF_IC_power = os.path.join(self.BIN_PATH, 'zero_RF_IC_power')
        toric_bin = self.TORIC_BIN
        prepare_eqdsk = self.GEQXPL_BIN

        cur_state_file = self.plasma_state_file
        cur_eqdsk_file = self.eqdsk_file
        toric_log = self.toric_log
        cwd = os.getcwd()

# Check if ICRF power is zero (or effectively zero).  If true don't run toric just
# run zero_RF_IC_power fortran code
        print('cur_state_file = ', cur_state_file)
        ps = NetCDFFile(cur_state_file, 'r')
        power_ic = ps.variables['power_ic'].getValue()[0]
        ps.close()
        print('power = ', power_ic)
        if -0.02 < power_ic < 0.02:
            retcode = subprocess.call([zero_RF_IC_power, cur_state_file])
            if (retcode != 0):
                print('Error executing ', prepare_input)
                self.services.error('Error executing zero_RF_IC_power')
                raise Exception('Error executing zero_RF_IC_power')

            # N.B. zero_RF_IC_power does not produce a complete set of TORIC output
            #      files.  This causes an error in stage_output_files().  To
            #      solve this we generate a dummy set of output files here with
            #      system call 'touch'
            for file in self.OUTPUT_FILES.split():
                subprocess.call(['touch', file])

# Check if ICRF power is negative.  If true don't run toric just
# retain power from previous time step i.e. leave sources untouched in the state.
# However power_ic needs to be reset back to positive

        elif power_ic < -0.02:
            print('continuing power from previous time step')
            ps.variables['power_ic'].assignValue(-power_ic)
            ps.close()

    # Or actually run TORIC

        else:

            # Call TORIC prepare_input to generate torica.inp
            retcode = subprocess.call([prepare_input, cur_state_file])  # , cur_eqdsk_file])
            if (retcode != 0):
                print('Error executing ', prepare_input)
                self.services.error('Error executing TORIC prepare_input')
                raise Exception('Error executing TORIC prepare_input')

            # Call xeqdsk_setup to generate eqdsk.out file
            print('prepare_eqdsk', prepare_eqdsk, cur_eqdsk_file)

            retcode = subprocess.call([prepare_eqdsk,
                                       '@equigs_gen', '/g_filename='+cur_eqdsk_file,
                                       '/equigs_filename=equigs.data'])
            if (retcode != 0):
                print('Error in call to prepare_eqdsk')
                self.services.error('Error executing TORIC prepare_eqdsk')
                raise Exception('Error executing TORIC prepare_eqdsk')

            # Launch TORIC executable
            print('toric processors = ', self.NPROC)
            cwd = services.get_working_dir()
            task_id = services.launch_task(self.NPROC, cwd, toric_bin, logfile=toric_log)
            retcode = services.wait_task(task_id)
            if (retcode != 0):
                print('Error executing command: ', toric_bin)
                self.services.error('Error executing TORIC')
                raise Exception('Error executing TORIC')

            # Call process_output
            retcode = subprocess.call([process_output, cur_state_file])
            if (retcode != 0):
                print('Error executing',  process_output)
                self.services.error('Error executing TORIC process_output')
                raise Exception('Error executing TORIC process_output')


# Merge partial plasma state containing updated IC data
        try:
            partial_file = cwd + '/RF_IC_' + cur_state_file
            services.merge_current_state(partial_file, logfile='log.update_state')
            print('merged TORIC plasma state data ', partial_file)
        except Exception:
            print('Error in call to merge_current_state(', partial_file, ')')
            self.services.error('Error in call to merge_current_state')
            raise Exception('Error in call to merge_current_state')

        # Archive output files
        try:
            services.stage_output_files(timeStamp, self.OUTPUT_FILES)
        except Exception as e:
            print('Error in call to stage_output_files()', e)
            self.services.error('Error in call to stage_output_files()')
            raise Exception('Error in call to stage_output_files()')

        return 0

# ------------------------------------------------------------------------------
#
# checkpoint function
# Saves plasma state files to restart directory
#
# ------------------------------------------------------------------------------

    def checkpoint(self, timestamp=0.0):
        print('rf_ic_toric.checkpoint() called')
        services = self.services
        services.save_restart_files(timestamp, self.RESTART_FILES)

# ------------------------------------------------------------------------------
#
# FINALIZE function
# As of now it does nothing
#
# ------------------------------------------------------------------------------

    def finalize(self, timestamp=0.0):
        print('toric.finalize() called')
