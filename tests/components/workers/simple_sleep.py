# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import time

from ipsframework import Component


class simple_sleep(Component):
    def step(self, timestamp=0.0, **keywords):
        time.sleep(1)
        self.services.wait_task(self.services.launch_task(1, '/tmp', '/bin/sleep', 1))
        time.sleep(1)
