from ipsframework import Component


class gpu_task(Component):
    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()

        self.services.wait_task(self.services.launch_task(1, cwd, self.EXE, '1_1', task_gpp=1))
        self.services.wait_task(self.services.launch_task(1, cwd, self.EXE, '1_2', task_gpp=2))
        self.services.wait_task(self.services.launch_task(1, cwd, self.EXE, '1_4', task_gpp=4))
        self.services.wait_task(self.services.launch_task(2, cwd, self.EXE, '2_2', task_gpp=2))
        self.services.wait_task(self.services.launch_task(4, cwd, self.EXE, '4_1', task_gpp=1))
