# -------------------------------------------------------------------------------
#  Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        print('Hello from HelloWorker - new1')
        subflow_config = self.SUB_WORKFLOW_CONFIG
        self.services.stage_input_files(subflow_config)
        override = {}
        override['PWD'] = self.services.get_config_param('PWD')
        with open(self.OUTPUT_FILES, 'w') as f:
            f.write("SUB INPUT FILE\n")
        (_, _, driver) = self.services.create_sub_workflow("Subflow_01", subflow_config, override)
        self.services.stage_input_files('')
        self.services.call(driver, 'init', '0.0')
        self.services.call(driver, 'step', '0.0')
        self.services.call(driver, 'finalize', '0.0')

        self.services.stage_subflow_output_files()
