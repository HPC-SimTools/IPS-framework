from ipsframework import Component


# pylint: disable=no-member,attribute-defined-outside-init
class timeloop_comp(Component):
    def init(self, timestamp=0.0, **keywords):
        self.output_files = self.OUTPUT_FILES.split()
        self.output_files.append(self.services.get_config_param("CURRENT_STATE"))
        self.services.stage_state()
        for output_file in self.output_files:
            with open(output_file, 'a') as f:
                f.write(f'{self.component_id} init()\n')
        self.services.update_state()

    def restart(self, timestamp=0.0, **keywords):
        self.services.log(f'restart({timestamp})')

        self.output_files = self.OUTPUT_FILES.split()
        self.output_files.append(self.services.get_config_param("CURRENT_STATE"))

        restart_root = self.services.get_config_param('RESTART_ROOT')
        restart_time = self.services.get_config_param('RESTART_TIME')
        self.services.get_restart_files(restart_root, restart_time, self.RESTART_FILES)

        self.services.stage_state()
        for output_file in self.output_files:
            with open(output_file, 'a') as f:
                f.write(f'{self.component_id} restart()\n')
        self.services.update_state()

    def step(self, timestamp=0.0, **keywords):
        self.services.log(f"step({timestamp})")
        self.services.stage_state()
        for output_file in self.output_files:
            with open(output_file, 'a') as f:
                f.write(f'{self.component_id} step({timestamp})\n')
        self.services.update_state()
        self.services.stage_output_files(timestamp, self.OUTPUT_FILES)

    def checkpoint(self, timestamp=0.0, **keywords):
        self.services.log(f'checkpoint({timestamp})')
        self.services.save_restart_files(timestamp, self.RESTART_FILES)
