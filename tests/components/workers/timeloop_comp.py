from ipsframework import Component


class timeloop_comp(Component):
    def init(self, timestamp=0.0):
        self.output_files = self.OUTPUT_FILES.split()
        self.output_files.append(self.services.get_config_param("CURRENT_STATE"))
        self.services.stage_state()
        for output_file in self.output_files:
            with open(output_file, 'a') as f:
                f.write(f'{self.component_id} init()\n')
        self.services.update_state()

    def step(self, timestamp=0.0):
        self.services.log(f"step({timestamp})")
        self.services.stage_state()
        for output_file in self.output_files:
            with open(output_file, 'a') as f:
                f.write(f'{self.component_id} step({timestamp})\n')
        self.services.update_state()

    def restart(self, timestamp=0.0):
        self.services.log(f'restart({timestamp})')

        # restart_root = config.get_global_param(self, services, 'RESTART_ROOT')
        # restart_time = config.get_global_param(self, services, 'RESTART_TIME')

        # self.services.get_restart_files(
        #     restart_root, restart_time, self.RESTART_FILES)

    def checkpoint(self, timestamp=0.0):
        self.services.log(f'checkpoint({timestamp})')
        self.services.save_restart_files(timestamp, self.RESTART_FILES)
