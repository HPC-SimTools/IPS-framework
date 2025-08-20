from sys import stderr

from ipsframework import Component


class driver(Component):
    """Note that only one worker component is called at a time, so the workers are not called in parallel."""

    def step(self, timestamp=0.0, **keywords):
        w = self.services.get_port('WORKER')
        # call the same worker step twice to check that the trace is correct
        self.services.call(w, 'step', 0)
        print('now performing second call at same timestep', file=stderr)
        self.services.info('now performing second call at same timestep')
        self.services.call(w, 'step', 0)
