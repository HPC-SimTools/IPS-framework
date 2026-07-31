"""
Component to be stepped in instance
"""

import csv
import sys
from time import time

from ipsframework import Component
from ipsframework.resource_helper import get_platform_info


class InstanceComponent(Component):
    def step(self, timestamp: float = 0.0, **keywords):
        start = time()

        # ENSEMBLE_INSTANCE is a special IPS variable that contains the
        # string uniquely identifying this instance.  Each instance will have
        # the `run_ensemble()` `name` argument prepended to a unique number
        # for each instance.  E.g., ENSEMBLE_INSTANCE might be "MY_INSTANCE_23".
        instance_id = self.services.get_config_param('ENSEMBLE_INSTANCE')
        self.services.info(f'{instance_id}: Start of step of instance component.')

        # Echo the parameters we're expecting, A, B, and C
        self.services.info(
            f'{instance_id}: instance component parameters: A={self.A}, B={self.B}, C={self.C}'
        )

        print(f'{instance_id}: A={self.A}, B={self.B}, C={self.C}')

        # Save some per-component stats
        run_env = get_platform_info()

        with open('stats.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['instance', 'executable', 'hostname', 'pid', 'core', 'start', 'end'])
            writer.writerow(
                [
                    instance_id,
                    sys.argv[0],
                    run_env['hostname'],
                    run_env['pid'],
                    run_env['core_id'],
                    start,
                    time(),
                ]
            )

        self.services.info(f'{instance_id}: End of step of instance component.')
