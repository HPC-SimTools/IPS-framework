#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
import os
import shutil
import ipsExceptions
import ipsutil
import subprocess

# import things to use event service
# from event_service_spec import PublisherEventService,SubscriberEventService,EventListener,Topic,EventServiceException

class DataManager(object):
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
        # create publisher event service object
        # self.publisherES = PublisherEventService()
        # get a topic to publish on
        #self.myTopic = self.publisherES.getTopic("test")
        self.myTopic = None
        self.outPrefix = ""
        self.simroot = ""
        self.statedir = ""
        self.plasmaStateFiles = []
        self.service_methods = ['stage_plasma_state',
                                'update_plasma_state',
                                'merge_current_plasma_state']
        self.fwk.register_service_handler(self.service_methods,
                                  getattr(self,'process_service_request'))

    def process_service_request(self, msg):
        """
        Invokes the appropriate public data manager method for the component
        specified in *msg*.  Return method's return value.
        """
        self.fwk.debug('Data Manager received message: %s', str(msg))
        method = getattr(self, msg.target_method)
        retval = method(msg)
        return retval

    def stage_plasma_state(self, msg):
        """
        Copy plasma state files from source dir to target dir.  Return 0.
        Exception raised on copy error.

        *msg.args*:

          0. plasma_files
          1. source_dir
          2. target_dir
        """
        plasma_files = msg.args[0]
        source_dir = msg.args[1]
        target_dir = msg.args[2]
        try:
            ipsutil.copyFiles(source_dir, plasma_files, target_dir)
        except Exception, e:
            self.fwk.exception('Error staging plasma state files to directory %s',
                               target_dir)
            raise
        return 0

    def update_plasma_state(self, msg):
        """
        Copy plasma state files from source dir to target dir.  Return 0.
        Exception raised on copy error.

        *msg.args*:

          0. plasma_files
          1. source_dir
          2. target_dir
        """
        plasma_files = msg.args[0]
        source_dir = msg.args[1]
        target_dir = msg.args[2]
        try:
            ipsutil.copyFiles(source_dir, plasma_files, target_dir)
        except Exception, e:
            self.fwk.exception( 'Error updating plasma state files from directory %s',
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

        #fwk_bin_path = sys.path[0]
        #update_state = os.path.join(fwk_bin_path, 'update_state')
	update_state = 'update_state'
        plasma_work_dir = os.path.dirname(target_state_file)
        component_work_dir = os.path.dirname(partial_state_file)
        current_plasma_state = os.path.basename(target_state_file)

        merge_stdout = sys.stdout
        if (log_file):
            log_fullpath = os.path.join(component_work_dir, log_file)
            try:
                merge_stdout = open(log_fullpath, 'w')
            except:
                self.fwk.exception('Error opening log file %s : using stdout',
                               log_fullpath)

        try:
            retval = subprocess.call([update_state, '-input', target_state_file,
                                  '-updates', partial_state_file],
                                  stdout = merge_stdout,
                                  stderr = subprocess.STDOUT)
        except Exception:
            self.fwk.exception( 'Error calling update_state - probably not found in $PATH')
            raise
            
        if (retval != 0):
            return retval
        try:
            ipsutil.copyFiles(plasma_work_dir, current_plasma_state, component_work_dir)
        except Exception, e:
            self.fwk.exception( 'Error refreshing local copy of current plasma state file in directory %s',
                                component_work_dir)
            raise
        return 0
