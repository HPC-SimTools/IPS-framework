import json
from sys import stderr

from ipsframework import Component

NOTEBOOK_1_TEMPLATE = 'basic.ipynb'


class Monitor(Component):
    """
    The monitor is able to read state files and will separately post data.
    """

    def init(self, timestamp=0.0):
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE])

        # Example of initializing two separate notebooks
        # Both notebooks should be initialized before the time loop and appended to inside the time loop
        self.services.initialize_jupyter_notebook(NOTEBOOK_1_TEMPLATE)

    def step(self, timestamp=0.0, **keywords):
        msg = f'Running Monitor step with timestamp={timestamp}'
        print(msg, file=stderr)
        self.services.send_portal_event(event_comment=msg)

        self.services.stage_state()

        state_file = self.services.get_config_param('STATE_FILES')

        # generate any analysis files from the state file you want
        with open(state_file) as f:
            analysis = json.load(f)

        # Do any preprocessing needed prior to adding any file to Jupyter
        # NOTE: you must make sure every analysis file name is unique in the "append" workflow

        # with the first analysis file, we just dump the results unmodified
        analysis_file_1 = f'{timestamp}_analysis.json'
        with open(analysis_file_1, 'w') as f:
            json.dump(analysis, f)

        # with the second analysis file, we'll just do a mock "analysis" where we just divide the values by two
        mapped_analysis = {key: value / 2 for key, value in analysis.items()}
        analysis_file_2 = f'{timestamp}_analysis_mapped.json'
        with open(analysis_file_2, 'w') as f:
            json.dump(mapped_analysis, f)

        print('add analysis data files')
        self.services.add_analysis_data_files(
            [analysis_file_1, analysis_file_2],
            timestamp=timestamp,
        )

    def finalize(self, timestamp=0.0): ...
