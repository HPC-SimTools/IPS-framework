#!/usr/bin/env python3
"""
    Component to be stepped in instance
"""
import os
from pathlib import Path

from ipsframework import Component


class InstanceComponent(Component):

    def step(self, timestamp: float = 0.0, **keywords):
        if 'HWLOC_XMLFILE' in os.environ:
            self.services.warning(f'HWLOC_XMLfile still set!')
        else:
            self.services.info('HWLOC_XMLFILE is not set')
        
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

        # We set the MPI executable path in the environment variable
        # MPI_STATS_EXEC in the `perlmutter.slurm` script that launches this
        # example. That way we don't have to play silly buggers figuring out
        # how many directory levels up to go to find the original python
        # script.
        mpi_executable = os.environ['MPI_STATS_EXEC']
        working_dir = str(Path('.').absolute())
        self.services.info(f'{instance_id}: Launching MPI executable '
                           f'{mpi_executable} in {working_dir}')
        args = ['-i', instance_id,
                '-s', str(self.B), # arbitrarily using B to specify sleep time
                '-o', 'stats.csv']
        cmd = str(mpi_executable) + ' ' + ' '.join(args)
        try:
            run_id = self.services.launch_task(nproc=5,
                                               working_dir=working_dir,
                                               binary=cmd)
        except Exception as e:
            self.services.critical(f'{instance_id}: Unable to launch '
                                   f'{mpi_executable}')

        self.services.wait_task(run_id)  # block until done

        self.services.info(f'{instance_id}: Completed MPI executable.')

        self.services.info(f'{instance_id}: End of step of instance '
                           f'component.')
