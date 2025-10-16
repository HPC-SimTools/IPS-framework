#!/usr/bin/env python3
"""
    Component to be stepped in instance
"""
from ips_framework import Component

class InstanceComponent(Component):
    
    def step(self, timestamp: float = 0.0, **keywords):
        # ENSEMBLE_INSTANCE is a special IPS variable that contains the
        # string uniquely identifying this instance.  Each instance will have
        # the `run_ensemble()` `name` argument prepended to a unique number
        # for each instance.  E.g., ENSEMBLE_INSTANCE might be "MY_INSTANCE_23".
        instance_id = self.services.get_config_param('ENSEMBLE_INSTANCE')
        self.services.info(f'{instance_id}: Start of step of instance '
                           f'component.')
        
        # Echo the parameters we're expecting, A, B, and C
        self.services.info(f'{instance_id}: instance component parameters: '
                           f'A={self.A}, B={self.B}, C={self.C}')

        self.services.info(f'{instance_id}: End of step of instance '
                           f'component.')