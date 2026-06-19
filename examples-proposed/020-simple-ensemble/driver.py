#!/usr/bin/env python3
"""
    Simple ensemble driver that just dispatches an IPS ensemble.
"""
from pathlib import Path

from ipsframework import Component


class EnsembleDriver(Component):
    """ Kicks off a simple ensemble """

    def step(self, timestamp=0.0):
        # Specifies different sets of variable values for concurrent ensemble
        # runs for a single component, 'a_comp'. In this case, the ensemble
        # instances have three different variables that each get set to three
        # different values, which means that there will be three IPS
        # instances to run each of those.  E.g.,

        # Instance  A   B       C
        # --------  -   ----    ------
        # 0         3   2.34    'bar'
        # 1         2   5.82    'baz'
        # 2         4   0.1     'quux'

        # In other examples in sibling directories we show how to use a CSV
        # file to supply these kinds of variable values as well as how to
        # support more than one component.  In any case, the format for manually
        # setting variables uses nested dictionary of dictionaries that contain
        # a list.  The top-level dictionary keys correspond to components, the
        # second-level dictionary keys are for the variables, and the lists
        # correspond to the variable values.  Naturally, the size of the lists
        # should be identical. Note that placeholders for these variables must
        # be defined in a special template IPS configuration file, in this case,
        # `template.conf`.
        variables = {
                'instance_component': {
                        'A': [3, 2, 4],
                        'B': [2.34, 5.82, 0.1],
                        'C': ['bar', 'baz', 'quux']}}

        # This is the IPS configuration file for the instances that looks like
        # a regular configuration file except there are slots for the 'A', 'B',
        # and 'C' for variable substitution.  'TEMPLATE' is specified in the
        # config file section for this driver.
        template = Path(self.config['TEMPLATE'])
        self.services.info(f'Using template config file {template}')

        if not template.exists():
            raise RuntimeError(f'{template} config template file does not exist')

        # Now spin up and run the instances. This function will return a list
        # with each list element corresponding to an instance.  You can use
        # this information to find the specific instance run directory for a
        # given set of variables.  E.g., the instance corresponding to
        # {'A' : 2, 'B' : 5.82, 'C' : 'baz'} is probably found in the
        # `INSTANCE_1` subdirectory.
        mapping = self.services.run_ensemble(template, variables,
                                             run_dir=Path('.').absolute(),
                                             name='INSTANCE_',
                                             num_nodes=1,
                                             cores_per_instance=1,
                                             logfile='stdout.txt',
                                             errfile='stderr.txt')
        # Print each mapping of instance name to what variable values were used.
        for instance in mapping:
            self.services.info(f'{instance!s}')