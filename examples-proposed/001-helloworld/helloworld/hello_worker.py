from ipsframework import Component


class hello_worker(Component):
    def __init__(self, services, config):
        """
        Automatically called from the IPS framework
        """
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0):
        """
        This function must be explicitly entered from your driver class.
        """
        print('Hello from hello_worker')
