# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from ipsframework import Component


class large_worker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timestamp=0.0, **keywords):
        print(self.__class__.__name__, ':', 'init() called')
        print('timestamp = ', timestamp)
        self.services.log('Initing Worker')
        return [self.__class__.__name__ + ':' + str(timestamp), 234]

    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
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

    def finalize(self, timestamp=0.0, **keywords):
        self.services.log('Finalizing Worker')

    def process_event(self, topicName, theEvent):
        print("Worker: processed ", (topicName, str(theEvent)))

    def terminate(self, status):
        self.services.log('Really Calling terminate()')
        Component.terminate(self, status)
