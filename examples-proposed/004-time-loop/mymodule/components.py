import json
import math
import os
import random
import time
from sys import stderr

from ipsframework import Component

DELAY = bool(os.environ.get('EXAMPLE_DELAY'))
REPLACE = bool(os.environ.get('EXAMPLE_REPLACE'))

# templates are existing files from the input directory
# names are what the notebook and the associated data file will be labeled with (you can leave off the .ipynb / .py)
NOTEBOOK_1_TEMPLATE = 'basic.ipynb'
NOTEBOOK_1_NAME = 'basic.ipynb'
NOTEBOOK_2_TEMPLATE = 'bokeh-plots.ipynb'
NOTEBOOK_2_NAME = 'bokeh-plots.ipynb'
DATA_MODULE_NAME = 'data_files'


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

        # Example of initializing two separate notebooks
        # Both notebooks should be initialized before the time loop and appended to inside the time loop
        self.services.initialize_jupyter_notebook(
            dest_notebook_name=NOTEBOOK_1_NAME,  # path is relative to JupyterHub directory
            source_notebook_path=NOTEBOOK_1_TEMPLATE,  # path is relative to input directory
            data_module_name=DATA_MODULE_NAME,
        )
        self.services.initialize_jupyter_notebook(
            dest_notebook_name=NOTEBOOK_2_NAME,  # path is relative to JupyterHub directory
            source_notebook_path=NOTEBOOK_2_TEMPLATE,  # path is relative to input directory
            data_module_name=DATA_MODULE_NAME,
        )

        # The time loop is configured in its own section of sim.conf
        # It is shared across all components
        for t in self.services.get_time_loop():
            self.services.update_time_stamp(t)
            self.services.call(worker, 'step', t)
            # TODO - perhaps monitor timestep does not need to be called every step, but only every 20 steps?
            self.services.call(monitor, 'step', t)

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
        if DELAY:
            print('simulating fake delay for 10 seconds', file=stderr)
            time.sleep(10.0)
        self.services.send_portal_event(event_comment=msg)

        self.services.stage_state()

        state_file = self.services.get_config_param('STATE_FILES')
        with open(state_file, 'rb') as f:
            data = f.read()

        # stage the state file in the JupyterHub directory and update the module file to handle it
        if REPLACE:
            self.services.add_analysis_data_file(state_file, os.path.basename(state_file), DATA_MODULE_NAME, replace=True)
        else:
            self.services.add_analysis_data_file(
                state_file,
                f'{timestamp}_{os.path.basename(state_file)}',
                DATA_MODULE_NAME,
                timestamp=timestamp,
            )

        print('SEND PORTAL DATA', timestamp, data, file=stderr)
        self.services.send_portal_data(timestamp, data)
