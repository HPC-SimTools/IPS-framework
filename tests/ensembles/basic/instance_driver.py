#!/usr/bin/env python3
"""
    Example driver for the ensembles example.

    Please note that run_ensemble can be run from any IPS component, not
    just a driver. The driver is used here for simplicity.
"""
from pathlib import Path

from ipsframework import Component


class instance_driver(Component):

    def __init__(self, services, config):
        super().__init__(services, config)
        print('Creating instance driver')

    def init(self, timeStamp=0.0):
        return

    def step(self, timestamp=0.0, **keywords):
        """ Run the ensemble instance workers

            In this example we have two components for an
            example coupled simulation.  The components are
            'a_sim_comp' and 'another_sim_comp'.  Here, we step
            each of those components where they echo their
            unique parameters.
        """
        self.services.info('Getting component ports')
        a_sim_comp = self.services.get_port('A_SIM_COMP')
        another_sim_comp = self.services.get_port('ANOTHER_SIM_COMP')

        self.services.info('Stepping components')
        self.services.call(a_sim_comp, 'step', 0.0)
        self.services.call(another_sim_comp, 'step', 0.0)

        self.services.info('Finished stepping components')

