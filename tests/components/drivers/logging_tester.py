from ipsframework import Component

log_types = ['log', 'debug', 'info', 'warning', 'error', 'exception', 'critical']


class logging_tester(Component):
    def init(self, timestamp=0.0, **keywords):
        print(f'{self.component_id}.init')
        for log_type in log_types:
            getattr(self.services, log_type)(f'init msg: {log_type}')

    def step(self, timestamp=0.0, **keywords):
        print(f'{self.component_id}.step')
        for log_type in log_types:
            getattr(self.services, log_type)(f'step msg: {log_type}')
            # with string formatting arguments
            getattr(self.services, log_type)(f'step msg: {log_type} timestamp=%d %s', timestamp, 'test')

    def finalize(self, timestamp=0.0, **keywords):
        print(f'{self.component_id}.finalize')
        for log_type in log_types:
            getattr(self.services, log_type)(f'finalize msg: {log_type}')
