#!/usr/bin/env python3
""" Component wrapper for the ensemble example for `a_sim`. """
from ipsframework import Component


class a_sim_comp(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0):
        # TODO echo parameters for this run
        print('Hello from a_sim_comp')

        # Echo the parameters we're expecting, A, B, and C
        print(f'a_sim_comp parameters: A={self.A}, B={self.B}, C={self.C}')
