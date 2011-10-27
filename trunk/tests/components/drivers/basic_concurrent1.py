"""
This test driver tests the basic functionality of a serial simulation.
It is designed to run a single simulation that has the same properties
as a typical SWIM run (similar number of input and output files, size
of components, resource requirements, etc.).  This test scenario should
always pass.
"""

from component import Component
import sys
import os
import time

class basic_concurrent1(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)

    def init(self, timestamp):
        self.services.log('Initing')
        return

    def step(self, timestamp):
        self.services.log('Stepping')

        services = self.services

        # set working directory and cd into it
        #services.setWorkingDirectory(self)

        # get references to components
        w1 = self.services.get_port('WORKER1')
        w2 = self.services.get_port('WORKER2')
        w3 = self.services.get_port('WORKER3')

        # should we do something different here?????  a try block?
        #if(w1 == None or w2 == None or w3 == None):
        #    print 'Error accessing physics components'
        #    raise Exception('Error accessing physics components')

        # ssf - get timeloop for simulation
        timeloop = [1, 2, 3]     # doesn't work yet..... services.getTimeLoop()
        tlist_str = ['%.2f'%t for t in timeloop]

        # ssf - call init for each component
        services.call(w1,'init', 0.0)
        services.call(w2,'init', 0.0)
        services.call(w3,'init', 0.0)

        # ssf - iterate through the timeloop
        for t in tlist_str:
            print 'Current time = ', t

            # ssf - call step for each component

            # in this simulation we have w2 and w3 dependent on w1
            # w2 and w3 can be run concurrently

            services.call(w1,'step', t)
            w2_call_id = services.call_nonblocking(w2,'step', t)
            w3_call_id = services.call_nonblocking(w3,'step', t)

            stuff = services.wait_call_list([w2_call_id, w3_call_id])

        # ssf - post simulation: call finalize on each component
        services.call(w1,'finalize', 99)
        services.call(w2,'finalize', 99)
        services.call(w3,'finalize', 99)
        return

    def process_event(self, topicName, theEvent):
        print "Driver: processed ", (topicName, str(theEvent))

    def terminate(self, status):
        self.services.log('Really Calling terminate()')
        Component.terminate(self, status)
