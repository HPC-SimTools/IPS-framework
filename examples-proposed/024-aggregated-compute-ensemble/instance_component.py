"""
Component to be stepped in instance.

This should generate a PNG image, a JSON file, and a CSV file.  The first
two are from synthetic data generated from `gen_data.py`.  The latter is
also generated from provenance data captured in `gen_data.py`, too.
"""

from pathlib import Path
from typing import Any

from ipsframework import Component


def create_cmd(
    instance: str, path: Path, alpha: float, l: float, t_final: float, nx: int, nt: int
) -> list[Any]:
    """create the command to run the external data generator

    :param instance: instance name
    :param path: path to data generator script directory
    :param alpha: thermal diffusivity
    :param l: domain length
    :param t_final: final time
    :param nx: number of spatial grid points
    :param nt: number of time steps
    :returns: list of command line arguments to be executed in step()
    """
    executable = path / 'gen_data.py'
    cmd = [
        'python3',
        str(executable),
        '--instance',
        instance,
        '--alpha',
        alpha,
        '--l',
        l,
        '--t_final',
        t_final,
        '--nx',
        nx,
        '--nt',
        nt,
    ]
    return cmd


class InstanceComponent(Component):
    def step(self, timestamp: float = 0.0, **keywords):
        # ENSEMBLE_INSTANCE is a special IPS variable that contains the
        # string uniquely identifying this instance.  Each instance will have
        # the `run_ensemble()` `name` argument prepended to a unique number
        # for each instance.  E.g., ENSEMBLE_INSTANCE might be "MY_INSTANCE_23".
        instance_id = self.services.get_config_param('ENSEMBLE_INSTANCE')
        self.services.info(f'{instance_id}: Start of step of instance component.')

        # Echo the parameters we're expecting, A, B, and C
        self.services.info(
            f'{instance_id}: instance component parameters: alpha={self.alpha}, l={self.l}, t_final={self.t_final}, nx={self.nx}, nt={self.nt}'
        )

        cmd = create_cmd(
            instance_id, Path(self.BIN_PATH), self.alpha, self.l, self.t_final, self.nx, self.nt
        )

        working_dir = str(Path('.').absolute())
        self.services.info(f'{instance_id}: Launching executable in {working_dir}')
        run_id = None
        try:
            cmd = ' '.join(cmd)  # need one big ole string for executing tasks
            run_id = self.services.launch_task(nproc=1, working_dir=working_dir, binary=cmd)
        except Exception:
            self.services.critical(f'{instance_id}: Unable to launch executable in {working_dir}')

        return_value = self.services.wait_task(run_id)  # block until done

        self.services.info(
            f'{instance_id}: Completed MPI executable with return value: {return_value}.'
        )

        # Add the generated data JSON and CSV files to the portal
        try:
            self.services.add_analysis_data_files(
                [f'{instance_id}_solution.json', f'{instance_id}_stats.csv'], replace=True
            )
        except Exception:
            print('did not add data files to portal, check logs')

        self.services.info(f'{instance_id}: End of step of instance component.')
