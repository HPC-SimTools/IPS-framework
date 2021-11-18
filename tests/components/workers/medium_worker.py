# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component
import os


class medium_worker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timestamp):
        print(self.__class__.__name__, ':', 'init() called')
        print('timestamp = ', timestamp)
        self.services.log('Initing Worker')
        return [self.__class__.__name__ + ':' + str(timestamp), 234]

    def step(self, timestamp):
        sleep_time = 1
        self.services.log('Stepping Worker timestamp=%s', timestamp)
        cwd = self.services.get_working_dir()
        pid = self.services.launch_task(int(self.NPROC),
                                        cwd,
                                        os.path.join(self.BIN_PATH, self.BIN),
                                        str(sleep_time),
                                        logfile='my_out'+timestamp)
        retval = self.services.wait_task(pid)
        return retval

    def finalize(self, timestamp):
        self.services.log('Finalizing Worker')

    def process_event(self, topicName, theEvent):
        print("Worker: processed ", (topicName, str(theEvent)))

    def terminate(self, status):
        self.services.log('Really Calling terminate()')
        Component.terminate(self, status)
