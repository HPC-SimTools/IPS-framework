# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from component import Component


class ResenbrockDriver(Component):

    def __init__(self, services, config):
        Component.__init__(self, services, config)

    def init(self, timestamp=0):
        print('init from dakota test driver')
        return

    def step(self, timestamp=0):
        print('step from dakota test driver')
        services = self.services
        services.stage_input_files(self.INPUT_FILES)
        x1 = float(self.X1)
        x2 = float(self.X2)
        sim_root = services.get_config_param('SIM_ROOT')
        result = 100.0 * (x2 - x1 * x1) * (x2 - x1 * x1) + (1. - x1) * (1. - x1)
        out_file = os.path.join(sim_root, 'RESULT')
        open(out_file, 'w').write('%.9f f' % (result))
        # time.sleep(0.5)
        return

    def finalize(self, timestamp=0):
        print('finalize from dakota test driver')
        # Driver finalize - nothing to be done
        pass
