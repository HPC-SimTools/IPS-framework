from ipsframework import Component


class Driver(Component):
    def step(self, timestamp=0.0):
        worker_comp = self.services.get_port('WORKER')
        self.services.call(worker_comp, 'step', 0.0)
