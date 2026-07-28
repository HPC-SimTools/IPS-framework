from ipsframework import Component


class HelloDriver(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0):
        print('HelloDriver: beginning step call')
        worker_comp = self.services.get_port('WORKER')
        self.services.call(worker_comp, 'step', 0.0)
        print('HelloDriver: finished step call')
