#!/usr/bin/env python3
"""
    Component to be stepped in instance
"""
from pathlib import Path
from time import time

from ipsframework import Component


class InstanceComponent(Component):

    def step(self, timestamp: float = 0.0, **keywords):
        start = time()

        # ENSEMBLE_INSTANCE is a special IPS variable that contains the
        # string uniquely identifying this instance.  Each instance will have
        # the `run_ensemble()` `name` argument prepended to a unique number
        # for each instance.  E.g., ENSEMBLE_INSTANCE might be "MY_INSTANCE_23".
        instance_id = self.services.get_config_param('ENSEMBLE_INSTANCE')
        self.services.info(f'{instance_id}: Start of step of instance '
                           f'component.')

        # Echo the parameters we're expecting, A, B, and C
        self.services.info(f'{instance_id}: instance component parameters: '
                           f'A={self.A}, B={self.B}, C={self.C}')

        # We have to go three directory levels up because we're working off
        # SIM_ROOT and the working directories that IPS constructed from there.
        # I would recommend to reduce confusion to use absolute paths to
        # any task executables.
        mpi_executable = '../../../mpi_stats.py'
        self.services.info(f'{instance_id}: Launching MPI executable: '
                           f'{mpi_executable}')
        args = ['-i', instance_id,
                '-s', str(self.B), # arbitrarily using B to specify sleep time
                '-o', 'stats.csv']
        cmd = str(mpi_executable) + ' ' + ' '.join(args)
        run_id = self.services.launch_task(nproc=1,
                                           working_dir=str(Path('.').absolute()),
                                           binary=cmd)

        self.services.wait_task(run_id)  # block until done

        self.services.info(f'{instance_id}: Completed MPI executable.')

        self.services.info(f'{instance_id}: End of step of instance '
                           f'component.')
