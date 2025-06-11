import shutil
import sys
from pathlib import Path

from ipsframework import Component

NOTEBOOK_1_TEMPLATE = 'parent.ipynb'
CHILD_CONFIG_TEMPLATE = 'child.conf'


class ParentWorkflowDriver(Component):
    def init(self, timestamp=0.0, **keywords):
        self.services.info('initializing')
        self.services.stage_input_files([NOTEBOOK_1_TEMPLATE, CHILD_CONFIG_TEMPLATE])
        self.services.initialize_jupyter_notebook(NOTEBOOK_1_TEMPLATE)
        self.services.info('initialized')

    def step(self, timestamp=0.0, **keywords):
        self.services.info('beginning step')

        # load initial config
        with open(CHILD_CONFIG_TEMPLATE, 'r') as f:
            base_child_config = f.read()

        # in this example, everything except for the generated child configuration is saved in this directory.
        base_example_directory = Path(self.services.get_config_param('SIM_ROOT')).parent

        # get configuration values from parent and pass them through to the child configs
        parent_portal_runid = self.services.get_config_param('PORTAL_RUNID')
        portal_url = self.services.get_config_param('PORTAL_URL')
        portal_api_key = self.services.get_config_param('PORTAL_API_KEY')

        # generate simulation config file for each child
        for k in range(1, 3):
            unique_child_config = f"""
SIM_ROOT = $PWD/sim_child_{k}
SIM_NAME = sim child {k}
RUN_ID = sim child {k}
PARENT_PORTAL_RUNID = {parent_portal_runid}
PORTAL_URL = {portal_url}
PORTAL_API_KEY = {portal_api_key}

# application-specific config variables
APPLICATION_MODIFIER = {2 << k}
"""

            with open(base_example_directory / f'child_{k}.conf', 'w') as f:
                f.write(unique_child_config)
                f.write(base_child_config)

        # execute tasks and wait on them
        ips_executable = shutil.which('ips.py')
        task_id_1 = self.services.launch_task(
            1,
            str(base_example_directory),
            sys.executable,
            ips_executable,
            '--platform',
            'platform.conf',
            '--config',
            'child_1.conf',
            '--log',
            'sim_child_1/ips.log',
        )
        task_id_2 = self.services.launch_task(
            1,
            str(base_example_directory),
            sys.executable,
            ips_executable,
            '--platform',
            'platform.conf',
            '--config',
            'child_2.conf',
            '--log',
            'sim_child_2/ips.log',
        )
        retcode_1 = self.services.wait_task(task_id_1)
        retcode_2 = self.services.wait_task(task_id_2)
        print('return code of task 1', retcode_1)
        print('return code of task 2', retcode_2)

    def finalize(self, timestamp=0.0, **keywords):
        self.services.info('finalized')
