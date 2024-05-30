import copy
from time import sleep
from sys import stderr

from ipsframework import Component


def myFun(*args):
    print(f'myFun({args[0]})')
    sleep(float(args[0]))
    print('function execution completed')
    return 0


class DaskWorker(Component):
    def step(self, timestamp=0.0):
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')

        duration = 0.5
        self.services.add_task('pool', 'binary', 1, cwd, self.EXECUTABLE, duration)
        self.services.add_task('pool', 'function', 1, cwd, myFun, duration)
        self.services.add_task('pool', 'method', 1, cwd, copy.copy(self).myMethod, duration)

        ret_val = self.services.submit_tasks('pool',
                                             use_dask=True,
                                             dask_nodes=1)
        print('ret_val =', ret_val, file=stderr)
        import time
        time.sleep(5.0)
        exit_status = self.services.get_finished_tasks('pool')
        print('exit_status = ', exit_status, file=stderr)

    def myMethod(self, *args):
        print(f'myMethod({args[0]})')
        sleep(float(args[0]))
        print('method execution completed')
        return 0
