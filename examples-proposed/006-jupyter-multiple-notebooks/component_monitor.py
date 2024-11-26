import json
import os
from sys import stderr

from ipsframework import Component

# templates are existing files from the input directory
# names are what the notebook and the associated data file will be labeled with (you can leave off the .ipynb / .py)
NOTEBOOK_1_TEMPLATE = 'basic.ipynb'
NOTEBOOK_2_TEMPLATE = 'bokeh-plots.ipynb'


# TODO - use two different examples instead of REPLACE loop
class Monitor(Component):
    """
    The monitor is able to read state files and will separately post data.
    """

    def init(self, timestamp=0.0):
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE, NOTEBOOK_2_TEMPLATE])

        # Example of initializing two separate notebooks
        # Both notebooks should be initialized before the time loop and appended to inside the time loop
        self.services.initialize_jupyter_notebook(
            dest_notebook_name=NOTEBOOK_1_TEMPLATE,  # path is relative to JupyterHub directory
            source_notebook_path=NOTEBOOK_1_TEMPLATE,  # path is relative to input directory
        )
        self.services.initialize_jupyter_notebook(
            dest_notebook_name=NOTEBOOK_2_TEMPLATE,  # path is relative to JupyterHub directory
            source_notebook_path=NOTEBOOK_2_TEMPLATE,  # path is relative to input directory
        )

    def step(self, timestamp=0.0, **keywords):
        msg = f'Running Monitor step with timestamp={timestamp}'
        print(msg, file=stderr)
        self.services.send_portal_event(event_comment=msg)

        self.services.stage_state()

        state_file = self.services.get_config_param('STATE_FILES')

        # Do some arbitrary processing and make sure analysis file is distinct from state file
        # i.e. just a sampling of the data
        # analysis file does NOT have to be a replica of the state file - we want the name to be unique

        # generate any analysis files from the state file you want
        with open(state_file) as f:
            analysis = json.load(f)

        analysis_file_1 = os.path.join(self.services.get_config_param('SIM_ROOT'), f'{timestamp}_analysis.json')
        with open(analysis_file_1, 'w') as f:
            json.dump(analysis, f)
        data = json.dumps(analysis).encode()

        self.services.add_analysis_data_files(
            [analysis_file_1],
            timestamp=timestamp,
        )

        print('SEND PORTAL DATA', timestamp, data, file=stderr)
        self.services.send_portal_data(timestamp, data)

    def finalize(self, timestamp=0.0):
        ...
