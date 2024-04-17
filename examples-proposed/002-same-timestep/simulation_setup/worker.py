# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import time
from ipsframework import Component


class simple_sleep(Component):
    def step(self, timestamp=0.0, **keywords):
        time.sleep(1)
        abspath = os.path.abspath(os.path.dirname(__file__))
        print(self.services.get_working_dir())
        self.services.wait_task(
            self.services.launch_task(1,
                                      abspath,
                                      f"{abspath}{os.path.sep}myscript",
                                      1)
        )
        time.sleep(1)
