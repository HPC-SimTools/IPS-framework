import copy
from time import sleep

from ipsframework import Component


def my_fun(*args):
    print(f'my_fun({args[0]})')
    sleep(float(args[0]))
    return 0


class DaskWorker(Component):
    def step(self, timestamp=0.0):
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')

        duration = 0.5
        self.services.add_task('pool', 'binary', 1, cwd, self.EXECUTABLE, duration)
        self.services.add_task('pool', 'function', 1, cwd, my_fun, duration)
        self.services.add_task('pool', 'method', 1, cwd, copy.copy(self).my_method, duration)

        ret_val = self.services.submit_tasks('pool', use_dask=True, dask_nodes=1)
        print('ret_val =', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        print('exit_status = ', exit_status)

    def my_method(self, *args):
        print(f'my_method({args[0]})')
        sleep(float(args[0]))
        return 0
