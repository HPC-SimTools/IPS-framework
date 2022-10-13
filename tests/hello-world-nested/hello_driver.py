# -------------------------------------------------------------------------------
#  Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component


class HelloDriver(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timestamp=0.0, **keywords):
        return

    def validate(self, timestamp=0.0, **keywords):
        return

    def step(self, timestamp=0.0, **keywords):
        try:
            worker_comp = self.services.get_port('WORKER')
        except Exception:
            self.services.exception('Error accessing worker component')
            raise
        self.services.call(worker_comp, 'step', 0.0)
        print('made it out of the worker call')

    def finalize(self, timestamp=0.0, **keywords):
        return
