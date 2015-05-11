#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------

from  component import Component

class HelloWorker(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)

    def init(self, timeStamp=0.0):
        return

    def validate(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        print 'Hello from HelloWorker - new'
        #fname = '/home/elwasif/Projects/SWIM/ipsframework-code/trunk/install/nested-test/hello_world_sub.config'
        (sim_name, init, driver) = self.services.create_sub_workflow('test_flow', self.SUB_WORKFLOW, {})
        self.services.stage_input_files(self.INPUT_FILES)

        print sim_name, init, driver
        print '#############################################'
        self.services.call(driver, 'init', '0.0')
        self.services.call(driver, 'step', '0.0')
        self.services.call(driver, 'finalize', '0.0')
        self.services.stage_subflow_output_files()
        return

    def finalize(self, timeStamp=0.0):
        return
