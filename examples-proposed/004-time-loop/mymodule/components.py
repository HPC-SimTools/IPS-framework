import json
import math
import random
from sys import stderr

from ipsframework import Component

NOTEBOOK_1_TEMPLATE = 'base-notebook-iterative.ipynb'
NOTEBOOK_1_NAME = 'full_state_iterative.ipynb'
NOTEBOOK_2_TEMPLATE = 'base-notebook-one-pass.ipynb'
NOTEBOOK_2_NAME = 'full_state_one_pass.ipynb'


class Init(Component):
    """Empty init component."""

    pass


class Driver(Component):
    """In this example, the driver iterates through the time loop and calls both the worker and the monitor component on each timestep."""

    def step(self, timestamp=0.0):
        worker = self.services.get_port('WORKER')
        monitor = self.services.get_port('MONITOR')

        self.services.call(worker, 'init', 0)
        # Needed for notebook template
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE, NOTEBOOK_2_TEMPLATE])

        # Example of a notebook we want to initialize and then periodically append to during the run
        self.services.initialize_jupyter_notebook(
            dest_notebook_name=NOTEBOOK_1_NAME,  # path is relative to JupyterHub directory
            source_notebook_path=NOTEBOOK_1_TEMPLATE,  # path is relative to input directory
        )
        # Initialize second notebook

        # The time loop is configured in its own section of sim.conf
        # It is shared across all components
        for t in self.services.get_time_loop():
            self.services.update_time_stamp(t)
            self.services.call(worker, 'step', t)
            # TODO - perhaps monitor timestep does not need to be called every step, but only every 20 steps?
            self.services.call(monitor, 'step', t)

        # With this second "example" notebook, we only create it once and only write to it once.
        self.services.initialize_jupyter_notebook(
            dest_notebook_name=NOTEBOOK_2_NAME,  # path is relative to JupyterHub directory
            source_notebook_path=NOTEBOOK_2_TEMPLATE,  # path is relative to input directory
            initial_data_files=self.services.get_staged_jupyterhub_files(),
        )

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

        # stage the state file in the JupyterHub directory
        data_file = self.services.jupyterhub_make_state(state_file, timestamp)
        print('ADD DATA FILE', data_file)
        self.services.add_data_file_to_notebook(NOTEBOOK_1_NAME, data_file)

        print('SEND PORTAL DATA', timestamp, data, file=stderr)
        self.services.send_portal_data(timestamp, data)
