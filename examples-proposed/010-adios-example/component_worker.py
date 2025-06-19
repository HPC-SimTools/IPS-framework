from sys import stderr

from adios2 import Stream

from ipsframework import Component

NOTEBOOK_1_TEMPLATE = 'analysis.ipynb'
ATTR = 'Greeting'


class Worker(Component):
    """
    The worker component performs computations and updates state files.
    """

    def init(self, timestamp=0.0):
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE])

        self.services.initialize_jupyter_notebook(NOTEBOOK_1_TEMPLATE)

    def step(self, timestamp=0.0):
        msg = f'Running Worker step with timestamp={timestamp}'
        print(msg, file=stderr)
        self.services.send_portal_event(event_comment=msg)

        outfile = f'adios_files_{timestamp}.bp'
        with Stream(outfile, 'w') as fh:
            fh.write(ATTR, 'Hello world')

        self.services.add_analysis_data_files([outfile], timestamp)

    def finalize(self, timestamp=0.0): ...
