#!/usr/bin/env python3
"""
    Example driver for the ensembles example.

    Please note that run_ensemble can be run from any IPS component, not
    just a driver. The driver is used here for simplicity.
"""
from pathlib import Path

from ipsframework import Component


class ensemble_driver(Component):

    def __init__(self, services, config):
        super().__init__(services, config)
        print('Creating driver')

    def init(self, timeStamp=0.0):
        return

    def step(self, timestamp=0.0, **keywords):
        """ set up and run the ensemble
        """
        # ENSEMBLE_DIR is an arbitrary variable denoting where we want to run
        # all the ensembles.  You don't have to use ENSEMBLE_DIR. You can
        # even hardcode the path here.  Whatever.
        run_dir = Path(self.services.get_config_param('ENSEMBLE_DIR'))
        self.services.info(f'Running ensemble in {run_dir}')

        # ENSEMBLE_PREFIX is an optional config variable for specifying
        # a string to prepend to the ensemble run directories and generated
        # files.  If not specified, the default is 'INSTANCE_n' where n is
        # is the arbitrary instance ID.
        prefix = self.services.get_config_param('ENSEMBLE_PREFIX',
                                                silent=True)
        if not prefix or prefix == '' or prefix == {}:
            self.services.info('No ensemble instance prefix specified. Using '
                               'default of INSTANCE_.')
            prefix = "INSTANCE_"
        else:
            self.services.info(f'Using ensemble instance prefix {prefix}')

        if not run_dir.exists():
            self.services.info(f'Creating {run_dir}')
            run_dir.mkdir(parents=True)

        template = Path(self.config['TEMPLATE'])
        self.services.info(f'Using template config file {template}')

        if not template.exists():
            raise RuntimeError(f'{template} config template file does not exist')

        # PLATFORM_CONFIG_FILE is a variable that points to the platform
        # config file used by the ensembles.  This could be the same
        # platform config file used for this driver, but it doesn't have to be.
        platform_config = self.config['PLATFORM_CONFIG_FILE']
        self.services.info(f'Using platform config file {platform_config}')

        # Specifies different sets of variable values for concurrent ensemble
        # runs for two different components, 'a_sim_comp' and
        # 'another_sim_comp', that correspond to two different coupled
        # simulations.  We chose two components to demonstrate that the same
        # variable, in this case 'B', can have different values for different
        # components. 'a_sim_comp' and 'another_sim_comp' are the names of
        # the config sections in the template file so we know where to look
        # for variable substitutions.
        variables = {'a_sim_comp': {'A': [3, 2, 4],
                                    'B': [2.34, 5.82, 0.1],
                                    'C': ['bar', 'baz', 'quux']},
                     'another_sim_comp': {'D': [7, 5, 9],
                                          'B': [0.775, 0.080, 29.2],
                                          'F': ['xyzzy', 'plud', 'thud']}}

        # Spins up N tasks, in this case three, each with a different set of
        # variable values. `mapping` is a data struct that associates the
        # specific simulation to a given run directory so that the user can
        # easily find output for a specific run.
        mapping = self.services.run_ensemble(template,
                                             variables,
                                             run_dir,
                                             platform_config,
                                             prefix)

        self.services.info(f'Mapping of dirs to parameters: {mapping!s}')


    def finalize(self, timeStamp=0.0):
        return

