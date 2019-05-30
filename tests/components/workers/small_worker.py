#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
import os
#import pytau
sys.path.append('../..')
from frameworkpath import *
sys.path.append(fsrc)
from component import Component

class small_worker(Component):
    def __init__(self, services, config):
        #self.timer = pytau.profileTimer('small_worker', "", str(os.getpid()))
        #pytau.start(self.timer)
        Component.__init__(self, services, config)
        print('Created %s' % (self.__class__))
        #pytau.stop(self.timer)

    def init(self, timestamp):
        #pytau.start(self.timer)
        print(self.__class__.__name__, ':', 'init() called')
        print('timestamp = ', timestamp)
        self.services.log('Initing Worker')
        #pytau.stop(self.timer)
        return [self.__class__.__name__+ ':'+ str(timestamp), 234]

    def step(self, timestamp):
        #pytau.start(self.timer)
        sleep_time = 1
        self.services.log('Stepping Worker boogity boogity', self.NPROC, self.BIN_PATH)
        pid = self.services.launch_task(int(self.NPROC), self.BIN_PATH, './parallel_sleep', str(sleep_time), logfile='my_out'+timestamp)
        retval = self.services.wait_task(pid)
        #pytau.stop(self.timer)
        return retval

    def finalize(self, timestamp):
        #pytau.start(self.timer)
        self.services.log('Finalizing Worker')
        #pytau.stop(self.timer)


    def process_event(self, topicName, theEvent):
        print("Worker: processed ", (topicName, str(theEvent)))

    def terminate(self, status):
        #pytau.start(self.timer)
        self.services.log('Really Calling terminate()')
        #pytau.stop(self.timer)  #need to stop the timer here because Component.terminate() will call sys.exit
        #pytau.dbDumpIncr('worker')
        Component.terminate(self, status)
