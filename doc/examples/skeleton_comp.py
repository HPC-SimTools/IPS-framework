# -------------------------------------------------------------------------------
#  Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

"""
This is a stripped down component that contains the boilerplate for creating a component and an outline of where other things go in comments.

"""

# ----------------------------------------------------------------------------
#  import modules
# ----------------------------------------------------------------------------

import os
from ipsframework import Component  # REQUIRED - all components inherit the IPS Component


class example(Component):  # CHANGE CLASS NAME

    def __init__(self, services, config):
        Component.__init__(self, services, config)
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

        # Optional - setup component's log file
        self.example_log = os.path.join(workdir, 'log.example')        # CHANGE EXAMPLE TO COMPONENT NAME

        # Copy plasma state files over to working directory
        # Get input files
        # Run any helper scripts
        # Archive output files to output tree to save your work

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

        # services = self.services
        # workdir = services.get_working_dir()

        # Get restart files listed in config file.
        # Get global configuration parameters and set internal data

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

        # services = self.services
        # workdir = services.get_working_dir()

        # Copy plasma state files over to working directory
        # Get input files
        # get the executables that will be run during step()
        # Call EXAMPLE prepare_input to generate the input files the executable is expecting
        # Launch EXAMPLE executable
        # check the return code or other mechanism to determine if the execution was successful
        # Call process_output
        # Merge partial plasma state containing updated IC data
        # Archive output files

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
