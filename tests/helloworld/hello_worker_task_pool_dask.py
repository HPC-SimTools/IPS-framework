# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import copy
from time import sleep

from distributed.diagnostics.plugin import WorkerPlugin

from ipsframework import Component


def my_fun(*args):
    print(f'my_fun({args[0]})')
    sleep(float(args[0]))
    return 0


class DaskWorkerPlugin(WorkerPlugin):
    def setup(self, worker):
        print('Running setup of worker')

    def teardown(self, worker):
        print('Running teardown of worker')


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0, **keywords):
        print('Hello from HelloWorker')

        exe = '/bin/sleep'
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        for i, duration in enumerate(('0.2', '0.4', '0.6')):
            self.services.add_task('pool', 'bin_' + str(i), 1, cwd, exe, duration)
            self.services.add_task(
                'pool', 'meth_' + str(i), 1, cwd, copy.copy(self).my_method, duration
            )
            self.services.add_task('pool', 'func_' + str(i), 1, cwd, my_fun, duration)

        worker_plugin = DaskWorkerPlugin()

        ret_val = self.services.submit_tasks(
            'pool', use_dask=True, dask_nodes=1, dask_ppw=10, dask_worker_plugin=worker_plugin
        )
        print('ret_val = ', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        print(exit_status)

    def my_method(self, *args):
        print(f'my_method({args[0]})')
        sleep(float(args[0]))
        return 0
