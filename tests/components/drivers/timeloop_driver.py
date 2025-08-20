from ipsframework import Component


class timeloop_driver(Component):
    def init(self, timestamp=0.0, **keywords):
        self.state_file = self.services.get_config_param('CURRENT_STATE')  # pylint: disable=attribute-defined-outside-init
        self.workers = [
            self.services.get_port(port)  # pylint: disable=attribute-defined-outside-init
            for port in self.services.get_config_param('PORTS')['NAMES'].split()
            if port not in ('INIT', 'DRIVER')
        ]

        mode = 'restart' if self.services.get_config_param('SIMULATION_MODE').lower() == 'restart' else 'init'

        if mode == 'init':
            with open(self.state_file, 'w') as f:
                f.write(f'{self.component_id} init()\n')
        else:
            self.services.stage_state()
            with open(self.state_file, 'a') as f:
                f.write(f'{self.component_id} restart()\n')
        self.services.update_state()

        for port in self.workers:
            self.services.call(port, mode, timestamp)

    def step(self, timestamp=0.0, **keywords):
        timeloop = self.services.get_time_loop()

        for t in timeloop:
            self.services.update_time_stamp(t)

            self.services.stage_state()
            with open(self.state_file, 'a') as f:
                f.write(f'{self.component_id} step({t})\n')
            self.services.update_state()

            for port in self.workers:
                self.services.call(port, 'step', t)

            self.services.checkpoint_components(self.workers, t)
            self.checkpoint(t)

        for port in self.workers:
            self.services.call(port, 'finalize', timeloop[-1])

    def checkpoint(self, timestamp=0.0, **keywords):
        self.services.log(f'checkpoint({timestamp})')
