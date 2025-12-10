#!/usr/bin/env python3
"""
Simple ensemble driver that just dispatches an IPS ensemble for an example
compute application.
"""

from pathlib import Path

from ipsframework import Component
from ipsframework.ipsutil import params_from_csv


class EnsembleDriver(Component):
    """Kicks off a simple ensemble"""

    def init(self, timestamp=0.0):
        pass
        # TODO temporarily commenting this out until the actual
        # example is ready to consider adding a notebook to the portal.

        # NOTEBOOK_TEMPLATE = 'notebook.ipynb'
        # self.services.stage_input_files([NOTEBOOK_TEMPLATE])
        # try:
        #     self.services.initialize_jupyter_notebook(NOTEBOOK_TEMPLATE)
        # except Exception:
        #     print('did not add notebook to portal')

    def step(self, timestamp=0.0):
        # This CSV file contains the parameters used for the
        # different instances.
        variables = params_from_csv(self.config['PARAMETER_FILE'])

        # This is the IPS configuration file for the instances that looks
        # like a regular configuration file except there are slots for the
        # variables (e.g., 'alpha', 'T_final', etc.).  'TEMPLATE' is
        # specified in the config file section for this driver.
        template = Path(self.config['TEMPLATE'])
        self.services.info(f'Using template config file {template}')

        if not template.exists():
            raise RuntimeError(
                f'{template} config template file does not exist')

        # Now spin up and run the instances. This function will return a list
        # with each list element corresponding to an instance.  You can use
        # this information to find the specific instance run directory for a
        # given set of variables.
        #
        # The "name" parameter must be unique for each ensemble within a run,
        # and will be used as an identifier on the Portal.
        mapping = self.services.run_ensemble(template, variables,
                                             run_dir=Path('.').absolute(),
                                             name='INSTANCE_',
                                             num_nodes=1, cores_per_instance=1)

        # Print each mapping of instance name to what variable values were used.
        for instance in mapping:
            self.services.info(f'{instance!s}')
