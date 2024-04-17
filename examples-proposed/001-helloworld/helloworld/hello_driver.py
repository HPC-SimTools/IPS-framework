from ipsframework import Component


class hello_driver(Component):
    """
    The IPS framework will always call into helloworld.hello_driver initially, as
    this module and name (helloworld.hello_driver.hello_driver) were defined in helloworld.conf
    """
    def __init__(self, services, config):
        """
        All component constructors are called before any functions are invoked.
        """
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0):
        print('hello_driver: beginning step call')
        worker_comp = self.services.get_port('WORKER')
        # call into the worker component
        self.services.call(worker_comp, 'step', timestamp)
        print('hello_driver: finished step call')
