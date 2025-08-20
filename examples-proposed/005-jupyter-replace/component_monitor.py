import json
from sys import stderr

from ipsframework import Component

# templates are existing files from the input directory
# names are what the notebook and the associated data file will be labeled with (you can leave off the .ipynb / .py)
NOTEBOOK_1_TEMPLATE = 'basic.ipynb'


class Monitor(Component):
    """
    The monitor is able to read state files and will separately post data.
    """

    def init(self, timestamp=0.0):
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE])

        # Initialize the notebook
        self.services.initialize_jupyter_notebook(NOTEBOOK_1_TEMPLATE)

    def step(self, timestamp=0.0, **keywords):
        msg = f'Running Monitor step with timestamp={timestamp}'
        print(msg, file=stderr)
        self.services.send_portal_event(event_comment=msg)

        self.services.stage_state()

        state_file = self.services.get_config_param('STATE_FILES')

        # generate any analysis files from the state file you want
        # since replace is true, do not worry about sending the same name of a file
        with open(state_file) as f:
            analysis = json.load(f)

        analysis_file_1 = 'analysis.json'
        with open(analysis_file_1, 'w') as f:
            json.dump(analysis, f)

        self.services.add_analysis_data_files([analysis_file_1], replace=True)

    def finalize(self, timestamp=0.0): ...
