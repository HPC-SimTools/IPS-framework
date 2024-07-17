import json
import math
import random
from sys import stderr

from ipsframework import Component


class Init(Component):
    """Empty init component."""

    pass


class Driver(Component):
    """In this example, the driver iterates through the time loop and calls both the worker and the monitor component on each timestep."""

    def step(self, timestamp=0.0):
        worker = self.services.get_port('WORKER')
        monitor = self.services.get_port('MONITOR')

        self.services.call(worker, 'init', 0)

        # The time loop is configured in its own section of sim.conf
        # It is shared across all components
        for t in self.services.get_time_loop():
            self.services.update_time_stamp(t)
            self.services.call(worker, 'step', t)
            # TODO - perhaps monitor timestep does not need to be called every step, but only every 20 steps?
            self.services.call(monitor, 'step', t)

        # create notebook here
        NOTEBOOK_NAME = 'full_state.ipynb'
        jupyter_files = self.services.get_staged_jupyterhub_files()
        self.services.create_jupyterhub_notebook(jupyter_files, NOTEBOOK_NAME)
        # NOTE: depending on the names of the files, you may have to use a custom mapping function to get the tag
        # You MUST store the tag somewhere in the file name
        tags = jupyter_files
        self.services.portal_register_jupyter_notebook(NOTEBOOK_NAME, tags)

        self.services.call(worker, 'finalize', 0)


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
            'y1': float,
            'y2': float,
            'y3': float,
        }

        data = {
            'y1': math.sin(self.start + timestamp / 50 * math.pi),
            'y2': math.sin(self.start + timestamp / 50 * math.pi) ** 2,
            'y3': math.sin(self.start + timestamp / 50 * math.pi) ** 3,
        }

        state_file = self.services.get_config_param('STATE_FILES')
        with open(state_file, 'w') as f:
            json.dump(data, f)

        self.services.update_state()


class Monitor(Component):
    """
    The monitor is able to read state files and will separately post data.
    """

    def step(self, timestamp=0.0, **keywords):
        msg = f'Running Monitor step with timestamp={timestamp}'
        print(msg, file=stderr)
        self.services.send_portal_event(event_comment=msg)

        self.services.stage_state()

        state_file = self.services.get_config_param('STATE_FILES')
        with open(state_file, 'rb') as f:
            data = f.read()

        # example of updating Jupyter state
        _jupyterhub_state_file = self.services.jupyterhub_make_state(state_file, timestamp)
        # if you wanted to create a notebook per timestep, call send_portal_data with _jupyterhub_state_file as the argument.
        print('SEND PORTAL DATA', timestamp, data, file=stderr)
        self.services.send_portal_data(timestamp, data)
