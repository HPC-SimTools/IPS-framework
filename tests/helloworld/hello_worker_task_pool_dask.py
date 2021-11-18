# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework import Component
from time import sleep
import copy


def myFun(*args):
    print(f"myFun({args[0]})")
    sleep(float(args[0]))
    return 0


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def init(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        print('Hello from HelloWorker')

        bin = '/bin/sleep'
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        for i, duration in enumerate(("0.2", "0.4", "0.6")):
            self.services.add_task('pool', 'bin_'+str(i), 1,
                                   cwd, bin, duration)
            self.services.add_task('pool', 'meth_'+str(i), 1,
                                   cwd, copy.copy(self).myMethod,
                                   duration)
            self.services.add_task('pool', 'func_' + str(i), 1,
                                   cwd, myFun, duration)

        ret_val = self.services.submit_tasks('pool', use_dask=True, dask_nodes=1, dask_ppn=10)
        print('ret_val = ', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        print(exit_status)

    def myMethod(self, *args):
        print(f"myMethod({args[0]})")
        sleep(float(args[0]))
        return 0

    def finalize(self, timeStamp=0.0):
        return
