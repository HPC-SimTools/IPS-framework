from sys import stderr

from ipsframework import Component


class driver(Component):
    def step(self, timestamp=0.0, **keywords):
        w = self.services.get_port('WORKER')
        # call the same worker step twice to check that the trace is correct
        for t in self.services.get_time_loop():
            # note that we can provide any arbitrary keyword arguments we like in our function call.
            # In this instance, we provide a different script to execute across two function calls.
            # You can use any keyword except for "timestamp".
            self.services.call(w, 'step', t, script_name='multiply_script.sh')
            print('now performing second call at same timestamp', timestamp, file=stderr)
            self.services.call(w, 'step', t, script_name='xor_script.sh')
