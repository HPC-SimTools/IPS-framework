#!/usr/bin/env python3
"""
Driver component for instances
"""

from ipsframework import Component

# The notebook that will be copied for each ensemble instance
SOURCE_NOTEBOOK_NAME='instance_base_notebook.ipynb'


class InstanceDriver(Component):
    """
    Instance driver component that steps the main component
    """
    def init(self, timestamp: float = 0.0, **keywords):
        self.services.stage_input_files([SOURCE_NOTEBOOK_NAME])

        self.services.initialize_jupyter_notebook(
                dest_notebook_name='jupyterhub_instance_notebook.ipynb',
                source_notebook_path=SOURCE_NOTEBOOK_NAME,
        )


    def step(self, timestamp: float = 0.0, **keywords):
        instance_component = self.services.get_port('WORKER')

        self.services.call(instance_component, 'step', 0.0)
