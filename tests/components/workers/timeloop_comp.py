from ipsframework import Component


class timeloop_comp(Component):
    def step(self, timestamp=0.0):
        super().step(timestamp)
        self.services.log(f"step({timestamp})")

    def restart(self, timestamp=0.0):
        self.services.log(f'restart({timestamp})')

        # restart_root = config.get_global_param(self, services, 'RESTART_ROOT')
        # restart_time = config.get_global_param(self, services, 'RESTART_TIME')

        # self.services.get_restart_files(
        #     restart_root, restart_time, self.RESTART_FILES)

    def checkpoint(self, timestamp=0.0):
        self.services.log(f'checkpoint({timestamp})')
        # self.services.save_restart_files(timestamp, self.RESTART_FILES)
