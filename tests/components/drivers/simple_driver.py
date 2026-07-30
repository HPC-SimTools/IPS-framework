from ipsframework import Component


class Driver(Component):
    def step(self, timestamp=0.0, **keywords):
        w = self.services.get_port('WORKER')
        self.services.call(w, 'step', 0)
