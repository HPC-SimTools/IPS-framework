from ipsframework import Component


def func(x):
    return x+1


class bad_task_worker(Component):
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()
        pid = self.services.launch_task(1,
                                        cwd,
                                        42)
        self.services.wait_task(pid)


class bad_task_pool_worker1(Component):
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        self.services.add_task('pool', 'task', 1, cwd, 42)
        self.services.submit_tasks('pool')
        self.services.get_finished_tasks('pool')


class bad_task_pool_worker2(Component):
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()
        self.services.create_task_pool('pool')
        self.services.add_task('pool', 'task', 1, cwd, func, 1)
        self.services.submit_tasks('pool')
        self.services.get_finished_tasks('pool')


class exception_worker(Component):
    def step(self, timestamp=0.0, **keywords):
        raise RuntimeError('Runtime error')


class assign_protected_attribute(Component):
    def step(self, timestamp=0.0, **keywords):
        self.args = 0
