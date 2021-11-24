# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from ipsframework import Component


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timestamp=0.0, **keywords):
        return

    def step(self, timestamp=0.0, **keywords):
        print('Hello from HelloWorker')

    def finalize(self, timestamp=0.0, **keywords):
        return
