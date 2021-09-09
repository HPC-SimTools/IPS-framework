# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from math import exp
from ipsframework import Component


class GaussianWellDriver(Component):
    def step(self, timestamp=0):
        print('step from dakota test driver')
        self.services.stage_input_files(self.INPUT_FILES)
        x = float(self.X)
        sim_root = self.services.get_config_param('SIM_ROOT')
        result = -exp(-(x-0.5)**2)
        out_file = os.path.join(sim_root, 'RESULT')
        open(out_file, 'w').write('%.9f f' % (result))
