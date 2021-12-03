from ipsframework import Component


class openmp_worker(Component):
    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()

        self.services.wait_task(self.services.launch_task(1, cwd, "check-mpi.gnu.cori", logfile="log.01", errfile="err.01"))
        self.services.wait_task(self.services.launch_task(1, cwd, "check-mpi.gnu.cori", logfile="log.02", errfile="err.02", task_ppn=1))
        self.services.wait_task(self.services.launch_task(1, cwd, "check-mpi.gnu.cori", logfile="log.03", errfile="err.03", task_ppn=1, task_cpp=32))

        self.services.wait_task(self.services.launch_task(4, cwd, "check-mpi.gnu.cori", logfile="log.11", errfile="err.11"))
        self.services.wait_task(self.services.launch_task(4, cwd, "check-mpi.gnu.cori", logfile="log.12", errfile="err.12", task_ppn=4))
        self.services.wait_task(self.services.launch_task(4, cwd, "check-mpi.gnu.cori", logfile="log.13", errfile="err.13", task_ppn=4, task_cpp=8))

        self.services.wait_task(self.services.launch_task(32, cwd, "check-mpi.gnu.cori", logfile="log.21", errfile="err.21"))
        self.services.wait_task(self.services.launch_task(32, cwd, "check-mpi.gnu.cori", logfile="log.22", errfile="err.22", task_ppn=32))
        self.services.wait_task(self.services.launch_task(32, cwd, "check-mpi.gnu.cori", logfile="log.23", errfile="err.23", task_ppn=32, task_cpp=1))

        self.services.wait_task(self.services.launch_task(4, cwd, "check-mpi.gnu.cori", logfile="log.31", errfile="err.31", task_ppn=8))
        self.services.wait_task(self.services.launch_task(4, cwd, "check-mpi.gnu.cori", logfile="log.33", errfile="err.32", task_ppn=4, task_cpp=4))
        self.services.wait_task(self.services.launch_task(4, cwd, "check-mpi.gnu.cori", logfile="log.32", errfile="err.33", task_ppn=4, task_cpp=2))

        self.services.wait_task(self.services.launch_task(4, cwd, "check-hybrid.gnu.cori", logfile="log.41", errfile="err.41", task_ppn=8))
        self.services.wait_task(self.services.launch_task(4, cwd, "check-hybrid.gnu.cori", logfile="log.42", errfile="err.42", task_ppn=4, task_cpp=4))
        self.services.wait_task(self.services.launch_task(4, cwd, "check-hybrid.gnu.cori", logfile="log.43", errfile="err.43", task_ppn=4, task_cpp=2))
