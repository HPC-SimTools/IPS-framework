# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from ipsframework.component import Component


class HelloDriver(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print('Created %s' % (self.__class__))

    def init(self, timeStamp=0.0):
        print('HelloDriver: init')
        try:
            worker_comp = self.services.get_port('WORKER')
        except Exception:
            self.services.exception('Error accessing worker component')
            raise
        self.services.call(worker_comp, 'init', 0.0)
        print('HelloDriver: finished worker init call')
        return

    def step(self, timeStamp=0.0):
        print('HelloDriver: beginning step call')
        try:
            worker_comp = self.services.get_port('WORKER')
        except Exception:
            self.services.exception('Error accessing worker component')
            raise
        self.services.call(worker_comp, 'step', 0.0)
        print('HelloDriver: finished worker call')
        return

    def finalize(self, timeStamp=0.0):
        return
