#!/usr/bin/env python3
"""
    Simple ensemble driver that just dispatches an IPS ensemble.
"""
from pathlib import Path

from ipsframework import Component
from ipsframework.ipsutil import params_from_csv

class EnsembleDriver(Component):
    """ Kicks off an ensemble using variables from a CSV file. """

    def step(self, timestamp=0.0):
        # Read in the variable combinations from a CSV file.  The CSV file
        # contains the same instance values as shown in
        # `example-proposed/020-simple-ensemble`.  WARNING: if you use
        # relative paths, as is done here, ensure that you know where this
        # component is being run from, as the current working directory may not
        # be what you expect.  When I run this example from the top-level IPS
        # directory, this is the path I'm actually in: `/global/u1/m/mcoletti/\
        # projects/IPS/IPS-framework/examples-proposed/021-ensembles-from-CSV/\
        # ENSEMBLES/work/DRIVER__EnsembleDriver_1`, and the CSV file was
        # really in `021-ensembles-from-CSV`.  Therefore, I suggest using
        # absolute paths or constructing paths using `Path` objects to avoid
        # confusion.
        variables = params_from_csv('../../../variables.csv')

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
                                             cores_per_instance=2)
        # Print each mapping of instance name to what variable values were used.
        for instance in mapping:
            self.services.info(f'{instance!s}')