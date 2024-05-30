from ipsframework import Component


class openmp_task(Component):
    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()

        mpi = '/usr/common/software/bin/check-mpi.gnu.cori'
        hybrid = '/usr/common/software/bin/check-hybrid.gnu.cori'

        self.services.wait_task(self.services.launch_task(1, cwd, mpi, logfile='log.01', errfile='err.01', omp=True))
        self.services.wait_task(self.services.launch_task(1, cwd, mpi, logfile='log.02', errfile='err.02', task_ppn=1, omp=True))
        self.services.wait_task(self.services.launch_task(1, cwd, mpi, logfile='log.03', errfile='err.03', task_ppn=1, task_cpp=32, omp=True))

        self.services.wait_task(self.services.launch_task(4, cwd, mpi, logfile='log.11', errfile='err.11', omp=True))
        self.services.wait_task(self.services.launch_task(4, cwd, mpi, logfile='log.12', errfile='err.12', task_ppn=4, omp=True))
        self.services.wait_task(self.services.launch_task(4, cwd, mpi, logfile='log.13', errfile='err.13', task_ppn=4, task_cpp=8, omp=True))

        self.services.wait_task(self.services.launch_task(32, cwd, mpi, logfile='log.21', errfile='err.21', omp=True))
        self.services.wait_task(self.services.launch_task(32, cwd, mpi, logfile='log.22', errfile='err.22', task_ppn=32, omp=True))
        self.services.wait_task(self.services.launch_task(32, cwd, mpi, logfile='log.23', errfile='err.23', task_ppn=32, task_cpp=1, omp=True))

        self.services.wait_task(self.services.launch_task(4, cwd, mpi, logfile='log.31', errfile='err.31', task_ppn=8, omp=True))
        self.services.wait_task(self.services.launch_task(4, cwd, mpi, logfile='log.32', errfile='err.32', task_ppn=4, task_cpp=4, omp=True))
        self.services.wait_task(self.services.launch_task(4, cwd, mpi, logfile='log.33', errfile='err.33', task_ppn=4, task_cpp=2, omp=True))

        self.services.wait_task(self.services.launch_task(4, cwd, hybrid, logfile='log.41', errfile='err.41', task_ppn=8, omp=True))
        self.services.wait_task(self.services.launch_task(4, cwd, hybrid, logfile='log.42', errfile='err.42', task_ppn=4, task_cpp=4, omp=True))
        self.services.wait_task(self.services.launch_task(4, cwd, hybrid, logfile='log.43', errfile='err.43', task_ppn=4, task_cpp=2, omp=True))


class openmp_task_pool(Component):
    # pylint: disable=no-member
    def step(self, timestamp=0.0, **keywords):
        cwd = self.services.get_working_dir()

        self.services.create_task_pool('pool')

        mpi = '/usr/common/software/bin/check-mpi.gnu.cori'
        self.services.add_task('pool', 'task_1', 4, cwd, mpi, logfile='log.1', errfile='err.1', task_ppn=8, omp=True)
        self.services.add_task('pool', 'task_2', 4, cwd, mpi, logfile='log.2', errfile='err.2', task_ppn=4, task_cpp=4, omp=True)
        self.services.add_task('pool', 'task_3', 4, cwd, mpi, logfile='log.3', errfile='err.3', task_ppn=4, task_cpp=2, omp=True)

        self.services.submit_tasks('pool')
