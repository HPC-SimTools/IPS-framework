"""
    Example Driver for the ensembles example.

    Please note that run_ensemble can be run from any IPS component, not
    just a Driver. The Driver is used here for simplicity.
"""
from ipsframework import Component


class InstanceDriver(Component):

    def __init__(self, services, config):
        super().__init__(services, config)
        print('Creating instance Driver')

    def init(self, timeStamp=0.0):
        return

    def step(self, timestamp=0.0, **keywords):
        """ Run the ensemble instance workers

            In this example we have two components for an
            example coupled simulation.  The components are
            'ASimComp' and 'AnotherSimComp'.  Here, we step
            each of those components where they echo their
            unique parameters.
        """
        self.services.info('Getting component ports')
        a_comp = self.services.get_port('A_COMP')
        another_comp = self.services.get_port('ANOTHER_COMP')

        self.services.info('Stepping components')
        self.services.call(a_comp, 'step', 0.0)
        self.services.call(another_comp, 'step', 0.0)

        self.services.info('Finished stepping components')
