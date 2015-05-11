#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
import os
import time
sys.path.append('../..')
sys.path.append('..')
from frameworkpath import *
sys.path.append(fsrc)
from component import Component

class MCMDDriver(Component):
#class mcmd_driver(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)

    def init(self, timestamp):
        print timestamp
        p = self.services.get_port('WORKER')
        print p
        retval = self.services.call(p, 'init', '00.00')
        print 'MCMDDriver:init(): ', retval
        self.services.log('Initing')
        return

    def step(self, timestamp):
        #pid = self.services.launch_task(1, os.getcwd(), '/bin/ls', '-a', '-l')
        #self.services.stage_input_files(self.INPUT_FILES)
        #self.services.update_plasma_state()
        #self.services.stage_output_files(timestamp, self.OUTPUT_FILES)
        self.services.log('Stepping')
        p = self.services.get_port('WORKER')
        retval = self.services.call(p, 'step', '01.00')
        print 'retval of worker step: ', retval

        # Need to fix timeloop invocation....
        #self.services.get_timeloop()
#        eventBody = {}
#        eventBody["bond"] = "007"
#        self.services.publish("hello world", "here i come", eventBody)
#        self.services.publish("hello world again", "here i come", eventBody)
#        self.services.publish("hello world", "here i come again", eventBody)
#        self.services.process_events()
#        self.services.subscribe("hello world", "process_event")
#        self.services.subscribe("hello world again", "process_event")
#        self.services.process_events()
#        self.services.unsubscribe("hello world")
#        self.services.unsubscribe("hello world again")
#        raise KeyError
        return

    def process_event(self, topicName, theEvent):
        print "Driver: processed ", (topicName, str(theEvent))

    def terminate(self, status):
        self.services.log('Really Calling terminate()')
        Component.terminate(self, status)
