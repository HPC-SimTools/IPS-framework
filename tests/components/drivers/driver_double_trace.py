from ipsframework import Component


class Driver(Component):
    def step(self, timestamp=0.0, **keywords):
        w = self.services.get_port('WORKER')
        # call the same worker step twice to check that the trace is correct
        self.services.call(w, 'step', 0)
        self.services.call(w, 'step', 0)
