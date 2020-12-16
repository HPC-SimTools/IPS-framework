# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
This test driver tests the basic functionality of a serial simulation.
It is designed to run a single simulation that has the same properties
as a typical SWIM run (similar number of input and output files, size
of components, resource requirements, etc.).  This test scenario should
always pass.
"""
from ipsframework import Component


class basic_serial1(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)

    def init(self, timestamp):
        self.services.log('Initing')
        return

    def step(self, timestamp):
        self.services.log('Stepping')

        services = self.services

        # set working directory and cd into it
        # services.setWorkingDirectory(self)

        # get references to components
        w1 = self.services.get_port('WORKER1')
        w2 = self.services.get_port('WORKER2')
        w3 = self.services.get_port('WORKER3')

        # should we do something different here?????  a try block?
        if(w1 is None or w2 is None or w3 is None):
            print('Error accessing physics components')
            raise Exception('Error accessing physics components')

        # ssf - get timeloop for simulation
        timeloop = services.get_time_loop()
        tlist_str = ['%.2f' % t for t in timeloop]

        # ssf - call init for each component
        services.call(w1, 'init', 0.0)
        services.call(w2, 'init', 0.0)
        services.call(w3, 'init', 0.0)

        # ssf - iterate through the timeloop
        for t in tlist_str:
            print('Current time = ', t)

            # ssf - call step for each component
            services.call(w1, 'step', t)
            services.call(w2, 'step', t)
            services.call(w3, 'step', t)

            # ssf - post step processing: stage plasma state, stage output
            # services.stage_plasma_state()
            # services.stage_output_files(t, self.OUTPUT_FILES)

        # ssf - post simulation: call finalize on each component
        services.call(w1, 'finalize', 99)
        services.call(w2, 'finalize', 99)
        services.call(w3, 'finalize', 99)
        return

    def process_event(self, topicName, theEvent):
        print("Driver: processed ", (topicName, str(theEvent)))

    def terminate(self, status):
        self.services.log('Really Calling terminate()')
        Component.terminate(self, status)
