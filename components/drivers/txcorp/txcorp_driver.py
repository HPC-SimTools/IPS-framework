#! /usr/bin/env python

# version 3.0 5/12/08 (Batchelor)

import sys
import os
import subprocess
import getopt
import shutil
import math
from component import Component
from Scientific.IO.NetCDF import *
import Numeric


class generic_driver(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)

# ------------------------------------------------------------------------------
#
# init function
#
# ------------------------------------------------------------------------------

    def init(self, timestamp=0):
        # Driver initialization ? nothing to be done
        return

# ------------------------------------------------------------------------------
#
# validate function
#
# ------------------------------------------------------------------------------

    def validate(self, timestamp=0):
        # Driver validate ? nothing to be done
        return

# ------------------------------------------------------------------------------
#
# step function
#
# ------------------------------------------------------------------------------

    def step(self, timestamp=0):

        services = self.services
        #self.services.setWorkingDirectory(self)
        self.services.stage_plasma_state()
        self.services.stage_input_files(self.INPUT_FILES)

       # Get references to the components to run in simulation

        epaComp = services.get_port('EPA')
        rfComp = services.get_port('RF_IC')
        fpComp = services.get_port('FP')

        if(epaComp == None):
            print 'Error accessing EPA component'
            sys.exit(1)
        if(rfComp == None):
            print 'Error accessing RF component'
            sys.exit(1)
        if(fpComp == None):
            print 'Error accessing FP component'
            sys.exit(1)

        # Get timeloop for simulation
        timeloop = services.get_time_loop()
        tlist_str = ['%.3f'%t for t in timeloop]
        t = tlist_str[0]

        # Call init for each component
        services.call(epaComp,'init', t)
        print 'epa init called'
        print (' ')

        services.call(rfComp,'init', t)
        print 'rf init called'
        print (' ')

        services.call(fpComp,'init', t)
        print 'fp init called'
        print (' ')

#      self.services.stage_plasma_state()
#      self.initStateAndPower(float(t))

        self.services.stage_plasma_state()
        cur_state_file = self.services.get_config_param('CURRENT_STATE')
        next_state_file = self.services.get_config_param('NEXT_STATE')
        shutil.copyfile(cur_state_file, next_state_file)
        services.update_plasma_state()

       # Post init processing: stage plasma state, stage output
        services.stage_output_files(t, self.OUTPUT_FILES)

        print ' init sequence complete--ready for time loop'
        # Iterate through the timeloop
        for t in tlist_str[1:len(timeloop)]:
            print (' ')
            print 'Driver: step to time = ', t
            services.updateTimeStamp(t)

            # call pre_step_logic
            services.stage_plasma_state()
            self.pre_step_logic(float(t))
            services.update_plasma_state()
            print (' ')

            # Call step for each component

            print (' ')
            services.call(rfComp,'step', t)

            print (' ')
            services.call(fpComp,'step', t)

            print (' ')
            services.call(epaComp,'step', t)

            self.services.stage_plasma_state()

            # Post step processing: stage plasma state, stage output
            services.stage_output_files(t, self.OUTPUT_FILES)

        # Post simulation: call finalize on each component
        # services.call(pre_step_logicComp, 'finalize')
        services.call(rfComp, 'finalize')
        services.call(fpComp, 'finalize')
        services.call(epaComp, 'finalize')

# ------------------------------------------------------------------------------
#
# finalize function
#
# ------------------------------------------------------------------------------

    def finalize(self, timestamp=0.0):
        # Driver finalize - nothing to be done
        pass

# "Private" driver methods

    def pre_step_logic(self, timeStamp):

        cur_state_file = self.services.get_config_param('CURRENT_STATE')
        prior_state_file = self.services.get_config_param('PRIOR_STATE')
        next_state_file = self.services.get_config_param('NEXT_STATE')

        #  Copy data from next plasma state to current plasma state
        shutil.copyfile(next_state_file, cur_state_file)

        # Update time stamps
        ps = NetCDFFile(cur_state_file, 'r+')
        t1 = ps.variables['t1'].getValue()
        self.services.log('ps%t1 = ', t1)

        power_ic = 0.0
        if ('power_ic' in ps.variables.keys()):
            power_ic = ps.variables['power_ic'].getValue()[0]

        ps.variables['t0'].assignValue(t1)
        ps.variables['t1'].assignValue(timeStamp)

        ps.close()
        shutil.copyfile(cur_state_file, prior_state_file)

        print'generic_driver pre_step_logic: timeStamp = ', timeStamp
        print'generic_driver pre_step_logic: power_ic = ', power_ic

        return
