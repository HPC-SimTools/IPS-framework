# -------------------------------------------------------------------------------
#  Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component


class HelloDriver(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        try:
            worker_comp = self.services.get_port('WORKER')
        except Exception:
            self.services.exception('Error accessing worker component')
            raise
        self.services.update_time_stamp(1)
        self.services.call(worker_comp, 'step', 0.0)
        with open(self.OUTPUT_FILES.split()[0], 'w') as f:
            f.write('SUB OUTPUT FILE\n')
        self.services.stage_output_files(timestamp, self.OUTPUT_FILES)
