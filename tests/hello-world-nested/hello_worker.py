# -------------------------------------------------------------------------------
#  Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timeStamp=0.0):
        return

    def validate(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        print('Hello from HelloWorker - new1')
        self.services.stage_input_files(self.SUB_WORKFLOW_CONFIG)
        subflow_config = self.SUB_WORKFLOW_CONFIG
        override = {}
        override['PWD'] = self.services.get_config_param('PWD')
        with open(self.OUTPUT_FILES, 'w') as f:
            f.write("SUB INPUT FILE\n")
        (sim_name, init, driver) = self.services.create_sub_workflow("Subflow_01", subflow_config, override)
        self.services.stage_input_files('')
        self.services.call(driver, 'init', '0.0')
        self.services.call(driver, 'step', '0.0')
        self.services.call(driver, 'finalize', '0.0')

        self.services.stage_subflow_output_files()

    def finalize(self, timeStamp=0.0):
        return
