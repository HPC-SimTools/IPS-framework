# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from component import Component
from numpy import random
import copy
from time import asctime, sleep


def myFun(*args):
    print(f"{asctime()} : Running myFUN {args}")
    sleep(int(args[0]))
    print(f"{asctime()} : Finished myFUN {args}")
    return 0


class HelloWorker(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print('Created %s' % (self.__class__))

    def init(self, timeStamp=0.0):
        return

    def validate(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        random.seed(1)
        SIZE = 10
        print('Hello from HelloWorker')
        duration = random.random_integers(1, high=20, size=SIZE)
        bin = "/bin/sleep"
        try:
            bin = self.CODE
        except Exception:
            pass
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        for i in range(SIZE):
            task_env = {}
            task_env["FOO"] = f"task_{i}_FOO"
            self.services.add_task('pool', 'binary_'+str(i), 1,
                                   cwd, bin, str(duration[i]),
                                   logfile=f"task_{i}.log",
                                   task_env=task_env)
            self.services.add_task('pool', 'method_'+str(i), 1,
                                   cwd, copy.copy(self).myMethod, str(duration[i]),
                                   task_env=task_env)
            self.services.add_task('pool', 'function_' + str(i), 1,
                                   cwd, myFun, str(duration[i]),
                                   task_env=task_env)

        ret_val = self.services.submit_tasks('pool', use_dask=True, dask_nodes=1, dask_ppn=10)
        print('ret_val = ', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        print(exit_status)

        print("====== Non Blocking ")
        for i in range(SIZE):
            self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, bin, duration[i])
        total_tasks = SIZE
        active_tasks = self.services.submit_tasks('pool', block=False)
        finished_tasks = 0
        while (finished_tasks < total_tasks):
            exit_status = self.services.get_finished_tasks('pool')
            print(exit_status)
            finished_tasks += len(exit_status)
            active_tasks -= len(exit_status)
            print('Active = ', active_tasks, 'Finished = ', finished_tasks)
#            if (finished_tasks >= 50):
#                self.services.remove_task_pool('pool')
#                break
            if (active_tasks + finished_tasks < total_tasks):
                new_active_tasks = self.services.submit_tasks('pool', block=False)
                active_tasks += new_active_tasks
                print('Active = ', active_tasks, 'Finished = ', finished_tasks)

        return

    def myMethod(self, *args):
        print(f"{asctime()} : Running myMethod {args} self.BIN_PATH = {self.BIN_PATH}")
        sleep(int(args[0]))
        print(f"{asctime()} : Finished myMethod {args} self.BIN_PATH = {self.BIN_PATH}")
        return 0

    def finalize(self, timeStamp=0.0):
        return
