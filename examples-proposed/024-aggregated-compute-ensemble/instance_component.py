#!/usr/bin/env python3
"""
Component to be stepped in instance
"""

import csv
import sys
from time import time
from typing import Any
from pathlib import Path

from ipsframework import Component
from ipsframework.resourceHelper import get_platform_info


def create_cmd(alpha: float, L:float, T_final:float, Nx:int, Nt:int) -> list[Any]:
    """ create the command to run the external data generator

    :param alpha: thermal diffusivity
    :param L: domain length
    :param T_final: final time
    :param Nx: number of spatial grid points
    :param Nt: number of time steps
    :returns: list of command line arguments to be executed in step()
    """
    cmd = ['gen_data.py', '--alpha', alpha, '--L', L, '--T_final', T_final,
           '--Nx', Nx, '--Nt', Nt]
    return cmd


class InstanceComponent(Component):
    def step(self, timestamp: float = 0.0, **keywords):
        start = time()

        # ENSEMBLE_INSTANCE is a special IPS variable that contains the
        # string uniquely identifying this instance.  Each instance will have
        # the `run_ensemble()` `name` argument prepended to a unique number
        # for each instance.  E.g., ENSEMBLE_INSTANCE might be "MY_INSTANCE_23".
        instance_id = self.services.get_config_param('ENSEMBLE_INSTANCE')
        self.services.info(f'{instance_id}: Start of step of instance component.')

        # Echo the parameters we're expecting, A, B, and C
        self.services.info(f'{instance_id}: instance component parameters: '
                           f'alpha={self.alpha}, L={self.L}, '
                           f'T_final={self.T_final}, Nx={self.Nx}, '
                           f'Nt={self.Nt}')

        cmd = create_cmd()

        working_dir = str(Path('.').absolute())
        self.services.info(f'{instance_id}: Launching executable '
                           f'in {working_dir}')
        run_id = None
        try:
            run_id = self.services.launch_task(nproc=2,
                                               working_dir=working_dir,
                                               binary=cmd)
        except Exception as e:
            self.services.critical(f'{instance_id}: Unable to launch '
                                   f'executable in {working_dir}')

        self.services.wait_task(run_id)  # block until done

        self.services.info(f'{instance_id}: Completed MPI executable.')


        # Save some per-component stats
        stats_fname = f'stats_{timestamp}.csv'
        run_env = get_platform_info()

        with open(stats_fname, 'w') as f:
            # Write run-time stats to a CSV as well as the runtime parameters
            # specific to this instance.
            writer = csv.writer(f)
            writer.writerow(
                    ['instance', 'executable', 'hostname', 'pid', 'core',
                     'affinity',
                     'alpha', 'L', 'T_final', 'Nx', 'Nt',
                     'start', 'end'])
            writer.writerow([instance_id, sys.argv[0], run_env['hostname'],
                             run_env['pid'], run_env['core_id'],
                             run_env['affinity'],
                             self.alpha, self.L, self.T_final, self.Nx, self.Nt,
                             start, time()])

        # TODO temporarily commenting this out until the actual
        # example is ready to consider adding data files to the portal.  This
        # originally came from code Lance wrote in a previous example.
        # try:
        #     self.services.add_analysis_data_files([data_fname, stats_fname], timestamp)
        # except Exception:
        #     print('did not add data files to portal, check logs')

        self.services.info(f'{instance_id}: End of step of instance component.')
