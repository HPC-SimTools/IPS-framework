# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from ipsframework import Component


class ResenbrockDriver(Component):

    def init(self, timestamp=0.0, **keywords):
        print('init from dakota test driver')

    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        print('step from dakota test driver')
        services = self.services
        services.stage_input_files(self.INPUT_FILES)
        x1 = float(self.X1)
        x2 = float(self.X2)
        sim_root = services.get_config_param('SIM_ROOT')
        result = 100.0 * (x2 - x1 * x1) * (x2 - x1 * x1) + (1. - x1) * (1. - x1)
        out_file = os.path.join(sim_root, 'RESULT')
        open(out_file, 'w').write('%.9f f' % (result))

    def finalize(self, timestamp=0.0, **keywords):
        print('finalize from dakota test driver')
