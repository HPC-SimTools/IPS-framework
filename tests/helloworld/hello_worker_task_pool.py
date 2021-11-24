# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from ipsframework import Component


class HelloWorker(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0, **keywords):
        print('Hello from HelloWorker')
        total_tasks = 3
        duration = list(range(total_tasks))

        exe = '/bin/sleep'
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        for i in range(total_tasks):
            self.services.add_task('pool', 'task_'+str(i), 1, cwd, exe, str(duration[i]))
        ret_val = self.services.submit_tasks('pool')
        print('ret_val = ', ret_val)
        exit_status = self.services.get_finished_tasks('pool')
        print(exit_status)

        print("====== Non Blocking ")
        for i in range(total_tasks):
            self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, exe, str(duration[i]))
        active_tasks = self.services.submit_tasks('pool', block=False)
        finished_tasks = 0
        while finished_tasks < total_tasks:
            exit_status = self.services.get_finished_tasks('pool')
            print(exit_status)
            finished_tasks += len(exit_status)
            active_tasks -= len(exit_status)
            print('Active = ', active_tasks, 'Finished = ', finished_tasks)
            if active_tasks + finished_tasks < total_tasks:
                new_active_tasks = self.services.submit_tasks('pool', block=False)
                active_tasks += new_active_tasks
                print('Active = ', active_tasks, 'Finished = ', finished_tasks)

        # Create task pool but then remove task pool, should terminate all tasks
        for i in range(total_tasks):
            self.services.add_task('pool', 'task_'+str(i), 1, cwd, exe, str(10000))
        ret_val = self.services.submit_tasks('pool', block=False)
        print('ret_val = ', ret_val)
        self.services.remove_task_pool('pool')
        try:
            self.services.get_finished_tasks('pool')
        except KeyError as e:
            print(f'KeyError({e})')

        # exclude following test for now
        """
        print("====== Non Blocking  2 ")
        for i in range(50):
            self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, exe, str(duration[i]))
        total_tasks = 50
        active_tasks = self.services.submit_tasks('pool', block=False)
        finished_tasks = 0
        while (finished_tasks <  total_tasks) :
            exit_status = self.services.get_finished_tasks('pool')
            print(exit_status)
            finished_tasks += len(exit_status)
            active_tasks -= len(exit_status)
            if (i < 99):
                i += 1
                self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, exe, str(duration[i]))
                total_tasks +=1
            print('Active = ', active_tasks, 'Finished = ', finished_tasks, 'Total = ', total_tasks)
#            if (finished_tasks >= 50):
#                self.services.remove_task_pool('pool')
#                break
            if (active_tasks + finished_tasks < total_tasks):
                new_active_tasks = self.services.submit_tasks('pool', block=False)
                active_tasks += new_active_tasks
                print('Active = ', active_tasks, 'Finished = ', finished_tasks)
        """
