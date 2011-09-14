#! /usr/bin/env python

import sys
import os
import subprocess
import getopt
import shutil
import math
from component import Component

class epaDriver(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)

    def init(self, timestamp=0):
        return

    def parse(self, timestamp=0):
        return

    def step(self, timestamp=0):
        services = self.services

        #services.setWorkingDirectory(self)
        pre_step_logicComp = services.getPort('PRE_STEP_LOGIC') 
        epaComp = services.get_port('EPA')
        nbComp = services.getPort('NB') 

        if(pre_step_logicComp == None):
            print 'Error accessing PRE_STEP_LOGIC component'
            sys.exit(1)
        if(epaComp == None):
            print 'Error accessing Equilibrium component'
            sys.exit(1)
        if(nbComp == None):
            print 'Error accessing NB component'
            sys.exit(1)

        timeloop = services.get_time_loop()
        tlist_str = ['%.3f'%t for t in timeloop] 
        t = tlist_str[0]

        services.call(pre_step_logicComp,'init', t)
        services.call(nbComp,'init', t) 
        services.call(epaComp,'init', t)

        for t in tlist_str[ 1 : len(timeloop) ]:
            print 'Current time = ', t

# call components
            services.call(pre_step_logicComp,'step', t) 
            services.call(nbComp,'step', t) 
            services.call(epaComp,'step', t)

        services.call(epaComp, 'finalize')
        services.call(nbComp, 'finalize')
        services.call(pre_step_logicComp, 'finalize')

    def finalize(self, timestamp=0.0):
        pass
