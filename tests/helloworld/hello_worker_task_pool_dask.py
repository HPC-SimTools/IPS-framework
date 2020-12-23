# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from ipsframework import Component
from numpy import random


class HelloWorker(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print('Created %s' % (self.__class__))

    def init(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        random.seed(1)
        print('Hello from HelloWorker')
        total_tasks = 10
        duration = random.random_integers(1, high=3, size=total_tasks)

        bin = '/bin/sleep'
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        for i in range(total_tasks):
            self.services.add_task('pool', 'task_'+str(i), 1, cwd, bin, str(duration[i]))
        ret_val = self.services.submit_tasks('pool', use_dask=True, dask_nodes=1, dask_ppn=10)
        print('ret_val = ', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        print(exit_status)

    def finalize(self, timeStamp=0.0):
        return
