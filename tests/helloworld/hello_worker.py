# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from ipsframework import Component


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        print('Hello from HelloWorker')
        return

    def finalize(self, timeStamp=0.0):
        return
