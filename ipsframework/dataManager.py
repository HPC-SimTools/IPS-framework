# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
import os
import subprocess
from . import ipsutil


class DataManager:
    """
    The data manager facilitates the movement and exchange of data files for
    the simulation.
    """
    # DM init

    def __init__(self, fwk):
        # ref to framework
        self.fwk = fwk
        self.ES = None
        self.TM = None
        self.RM = None
        self.CM = None
        self.host = self.fwk.host
        self.myTopic = None
        self.outPrefix = ""
        self.simroot = ""
        self.statedir = ""
        self.state_files = []
        self.service_methods = ['stage_state',
                                'update_state',
                                'merge_current_plasma_state']
        self.fwk.register_service_handler(self.service_methods,
                                          getattr(self, 'process_service_request'))

    def process_service_request(self, msg):
        """
        Invokes the appropriate public data manager method for the component
        specified in *msg*.  Return method's return value.
        """
        self.fwk.debug('Data Manager received message: %s', str(msg))
        method = getattr(self, msg.target_method)
        retval = method(msg)
        return retval

    def stage_state(self, msg):
        """
        Copy plasma state files from source dir to target dir.  Return 0.
        Exception raised on copy error.

        *msg.args*:

          0. state_files
          1. source_dir
          2. target_dir
        """
        state_files = msg.args[0]
        source_dir = msg.args[1]
        target_dir = msg.args[2]
        try:
            ipsutil.copyFiles(source_dir, state_files, target_dir)
        except Exception:
            self.fwk.exception('Error staging plasma state files to directory %s',
                               target_dir)
            raise
        return 0

    def update_state(self, msg):
        """
        Copy plasma state files from source dir to target dir.  Return 0.
        Exception raised on copy error.

        *msg.args*:

          0. state_files
          1. source_dir
          2. target_dir
        """
        state_files = msg.args[0]
        source_dir = msg.args[1]
        target_dir = msg.args[2]
        try:
            ipsutil.copyFiles(source_dir, state_files, target_dir)
        except Exception:
            self.fwk.exception('Error updating state files from directory %s',
                               source_dir)
            raise
        return 0

    def merge_current_plasma_state(self, msg):
        """
        Merge partial plasma state file with global master.  Newly updated
        plasma state copied to caller's workdir.
        Exception raised on copy error.

        *msg.args*:

          0. partial_state_file
          1. target_state_file
          2. log_file: stdout for merge process if not ``None``
        """
        partial_state_file = msg.args[0]
        target_state_file = msg.args[1]
        log_file = msg.args[2]
        update_state = msg.args[3]

        plasma_work_dir = os.path.dirname(target_state_file)
        component_work_dir = os.path.dirname(partial_state_file)
        current_plasma_state = os.path.basename(target_state_file)

        merge_stdout = sys.stdout
        if log_file:
            log_fullpath = os.path.join(component_work_dir, log_file)
            try:
                merge_stdout = open(log_fullpath, 'w')
            except Exception:
                self.fwk.exception('Error opening log file %s : using stdout',
                                   log_fullpath)

        try:
            retval = subprocess.call([update_state, '-input', target_state_file,
                                      '-updates', partial_state_file],
                                     stdout=merge_stdout,
                                     stderr=subprocess.STDOUT)
        except Exception:
            self.fwk.exception('Error calling update_state - probably not found in $PATH')
            raise

        if retval != 0:
            return retval
        try:
            ipsutil.copyFiles(plasma_work_dir, current_plasma_state, component_work_dir)
        except Exception:
            self.fwk.exception('Error refreshing local copy of current plasma state file in directory %s',
                               component_work_dir)
            raise
        return 0
