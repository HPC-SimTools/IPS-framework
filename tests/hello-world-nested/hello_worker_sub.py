# -------------------------------------------------------------------------------
#  Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0, **keywords):
        print('Hello from HelloWorker - sub')
        self.services.info('Hello from HelloWorker - sub')
