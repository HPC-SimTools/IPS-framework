import os
import time
from sys import stderr

from ipsframework import Component

DELAY = bool(os.environ.get('EXAMPLE_DELAY'))


class Driver(Component):
    """In this example, the driver iterates through the time loop and calls both the worker and the monitor component on each timestep."""

    def init(self, timestamp=0.0):
        self.worker = self.services.get_port('WORKER')
        self.monitor = self.services.get_port('MONITOR')

        self.services.call(self.worker, 'init', 0)
        self.services.call(self.monitor, 'init', 0)

    def step(self, timestamp=0.0):
        # The time loop is configured in its own section of sim.conf
        # It is shared across all components
        for t in self.services.get_time_loop():
            self.services.update_time_stamp(t)
            self.services.call(self.worker, 'step', t)
            if DELAY:
                print('simulating fake delay for 10 seconds', file=stderr)
                time.sleep(10.0)
            self.services.call(self.monitor, 'step', t)

    def finalize(self, timestamp=0.0):
        self.services.call(self.worker, 'finalize', 0)
        self.services.call(self.monitor, 'finalize', 0)
