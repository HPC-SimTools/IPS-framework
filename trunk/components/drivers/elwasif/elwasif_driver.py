#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
#! /usr/bin/env python

# ssf - some comments explaining each step would be helpful for users
#       I'll add what I *think* is going on.  Please correct me if I am wrong.

import sys
import os
import subprocess
import getopt
import shutil
import math
from component import Component

class testDriver(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)

    def init(self, timestamp=0):
        # ssf - insert additional init stuff here
        return

    def validate(self, timestamp=0):
        # ncd - meeting new interface standard for components
        return

    def step(self, timestamp=0):
        services = self.services

        # ssf - set working directory and cd into it
        #services.setWorkingDirectory(self)

        # ssf - get references to the components to run in simulation
        rfComp = services.get_port('RF_IC')
        profAdvanceComp = services.get_port('PROFILE_ADVANCE')

        if(rfComp == None or profAdvanceComp ==  None):
            print 'Error accessing physics components'
            sys.exit(1)

        # ssf - get timeloop for simulation
        timeloop = services.get_time_loop()
        tlist_str = ['%.2f'%t for t in timeloop]

        # ssf - call init for each component
        services.call(rfComp,'init')
        services.call(profAdvanceComp,'init')

        # ssf - iterate through the timeloop
        for t in tlist_str:
            print 'Current time = ', t

            # ssf - call step for each component
            services.call(rfComp,'step', t)
            services.call(profAdvanceComp,'step', t)

            # ssf - post step processing: stage plasma state, stage output
            services.stage_plasma_state()
            services.stage_output_files(t, self.OUTPUT_FILES)

        # ssf - post simulation: call finalize on each component
        services.call(rfComp, 'finalize')
        services.call(profAdvanceComp, 'finalize')

    def finalize(self, timestamp=0.0):
        # ssf - insert additional post simulation processing here
        pass
