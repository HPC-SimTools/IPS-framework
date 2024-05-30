from ipsframework import Component


class Driver(Component):
    """In this instance, the driver allows for the worker component to handle all parallel orchestration."""

    def step(self, timestamp=0.0):
        worker_comp = self.services.get_port('WORKER')
        self.services.call(worker_comp, 'step', 0.0)
