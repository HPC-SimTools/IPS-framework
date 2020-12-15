from ipsframework import Component

log_types = ["log",
             "debug",
             "info",
             "warning",
             "error",
             "exception",
             "critical"]


class logging_tester(Component):

    def init(self, timestamp):
        for log_type in log_types:
            getattr(self.services, log_type)(f'init msg: {log_type}')

    def step(self, timestamp):
        for log_type in log_types:
            getattr(self.services, log_type)(f'step msg: {log_type}')

    def finalize(self, timestamp):
        for log_type in log_types:
            getattr(self.services, log_type)(f'finalize msg: {log_type}')
