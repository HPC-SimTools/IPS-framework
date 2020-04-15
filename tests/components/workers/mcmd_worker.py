#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
import os
sys.path.append('../..')
from frameworkpath import *
sys.path.append(fsrc)
from component import Component

class MCMDWorker(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)

    def init(self, timestamp):
        print(self.__class__.__name__, ':', 'init() called')
        print('timestamp = ', timestamp)
        self.services.log('Initing Worker')
        return [self.__class__.__name__+ ':'+ str(timestamp), 234]

    def step(self, timestamp):
        self.services.log('Stepping Worker')
        pid = self.services.launch_task(1, os.getcwd(), '/bin/ls', '-a', '-l')
        return #self.services.wait_task(pid)

    def finalize(self, timestamp):
        self.services.log('Finalizing Worker')

    def process_event(self, topicName, theEvent):
        print("Worker: processed ", (topicName, str(theEvent)))

    def terminate(self, status):
        self.services.log('Really Calling terminate()')
        Component.terminate(self, status)
