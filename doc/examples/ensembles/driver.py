"""
    Example Driver for the ensembles example.

    Please note that run_ensemble can be run from any IPS component, not
    just a Driver. The Driver is used here for simplicity.
"""
import os
from pathlib import Path

from ipsframework import Component


class EnsembleDriver(Component):

    def __init__(self, services, config):
        super().__init__(services, config)
        print('Creating Driver')

    def init(self, timeStamp=0.0):
        return

    def step(self, timestamp=0.0, **keywords):
        """ set up and run the ensemble
        """
        self.services.info(f'Running ensemble in {os.getcwd()}')

        # Specifies different sets of variable values for concurrent ensemble
        # runs for two different components, 'a_comp' and
        # 'another_comp', that correspond to two different components
        # We chose two components to demonstrate that the same
        # variable, in this case 'B', can have different values for different
        # components. 'a_comp' and 'another_comp' are the names of
        # the config sections in the template file so we know where to look
        # for variable substitutions.
        variables = {'a_comp': {'A': [3, 2, 4],
                                'B': [2.34, 5.82, 0.1],
                                'C': ['bar', 'baz', 'quux']},
                     'another_comp': {'D': [7, 5, 9],
                                      'B': [0.775, 0.080, 29.2],
                                      'F': ['xyzzy', 'plud', 'thud']}}

        # If this approach is too cumbersome an alternative is to use an
        # IPS convenience function to read a CSV file, ipsutil.params_from_csv()
        # If you do this, you might want to add "input.csv" to
        # INPUT_FILES in the config file so that it is copied to the run.
        # e.g.,:
        # variables = ipsutil.params_from_csv('input.csv')

        # Spins up N tasks, in this case three, each with a different set of
        # variable values. `mapping` is a data struct that associates the
        # specific simulation to a given run directory so that the user can
        # easily find output for a specific run.  Note that "template.config"
        # is in INPUT_FILE for the Driver component so that it is copied to the run.
        # But, of course, you could also use a full path to the file, instead.
        mapping = self.services.run_ensemble('template.config', variables,
                                             '/tmp/IPS', name="EXAMPLE_",
                                             num_nodes=1)

        self.services.info(f'Mapping of dirs to parameters: {mapping!s}')


    def finalize(self, timeStamp=0.0):
        return
