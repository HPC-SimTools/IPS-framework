# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

from ipsframework import Component


class HelloWorker(Component):
    def step(self, timeStamp=0.0):
        print('Hello from HelloWorker')

        cwd = self.services.get_working_dir()

        print('Starting tasks =', len(self.services.task_map))

        # launch single task, wait_task
        task_id = self.services.launch_task(1, cwd, '/bin/sleep', '1')

        print('Number of tasks =', len(self.services.task_map))
        ret_val = self.services.wait_task(task_id, True)
        print('wait_task ret_val =', ret_val)

        # launch multiple tasks, wait_tasklist
        running_tasks = []
        for _ in range(2):
            task_id = self.services.launch_task(1, cwd, '/bin/sleep', '1')
            running_tasks.append(task_id)

        print('Number of tasks =', len(self.services.task_map))
        ret_val = self.services.wait_tasklist(running_tasks, True)
        print('wait_tasklist ret_val =', ret_val)
        print('Number of tasks =', len(self.services.task_map))

        # launch single task, kill_task
        task_id = self.services.launch_task(1, cwd, '/bin/sleep', '100')

        print('Number of tasks =', len(self.services.task_map))
        print('kill_task')
        self.services.kill_task(task_id)
        print('Number of tasks =', len(self.services.task_map))

        # launch multiple tasks, kill_all_tasks
        running_tasks = []
        for _ in range(2):
            task_id = self.services.launch_task(1, cwd, '/bin/sleep', '100')
            running_tasks.append(task_id)

        print('Number of tasks =', len(self.services.task_map))
        print('kill_all_tasks')
        self.services.kill_all_tasks()
        print('Number of tasks =', len(self.services.task_map))
