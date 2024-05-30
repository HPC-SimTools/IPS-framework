# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import time
from ipsframework import Component


class simple_sleep(Component):
    def step(self, timestamp=0.0, **keywords):
        this_dir = self.services.get_config_param('SIM_ROOT')
        self.services.wait_task(
            self.services.launch_task(1,
                                      this_dir,
                                      f'{this_dir}{os.path.sep}myscript',
                                      1)
        )
