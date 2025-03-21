import json
import math
import random

from ipsframework import Component

NOTEBOOK_1_TEMPLATE = 'child.ipynb'


class ChildWorkflowDriver(Component):
    def init(self, timestamp=0.0):
        self.services.info('initializing')
        self.application_modifier = int(self.services.get_config_param('APPLICATION_MODIFIER'))
        """Unique variable determined at runtime from the parent component which determines work"""
        self.cache = {}
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE])
        """keep track of the work in-memory until we want to finalize"""
        self.services.info('initialized')

    def step(self, timestamp=0.0):
        """Do arbitrary work to modify the local cache in-place"""
        for t in self.services.get_time_loop():
            self.cache[math.floor(t)] = t * self.application_modifier * random.random()

    def finalize(self, timestamp=0.0):
        """Write the final state to the destination file for the parent component to read, and save the final data"""
        OUTPUT_LOCATION = 'analysis.json'
        with open(OUTPUT_LOCATION, 'w') as f:
            json.dump(self.cache, f)
        self.services.add_analysis_data_files([OUTPUT_LOCATION])

        self.services.info('finalize')
