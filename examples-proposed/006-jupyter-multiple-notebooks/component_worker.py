import json
import math
import random
from sys import stderr

from ipsframework import Component


class Worker(Component):
    """
    The worker component performs computations and updates state files.
    """

    def init(self, timestamp=0.0):
        self.start = random.random() * math.pi * 2

    def step(self, timestamp=0.0):
        msg = f'Running Worker step with timestamp={timestamp}'
        print(msg, file=stderr)
        self.services.send_portal_event(event_comment=msg)

        data = {
            'y1': math.sin(self.start + timestamp / 50 * math.pi),
            'y2': math.sin(self.start + timestamp / 50 * math.pi) ** 2,
            'y3': math.sin(self.start + timestamp / 50 * math.pi) ** 3,
        }

        # TODO maybe assume that it's just one?
        state_file = self.services.get_config_param('STATE_FILES')
        with open(state_file, 'w') as f:
            json.dump(data, f)
        self.services.update_state()

    def finalize(self, timestamp=0.0): ...
