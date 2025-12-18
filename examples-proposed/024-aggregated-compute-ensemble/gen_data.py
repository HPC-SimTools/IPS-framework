#!/usr/bin/env python3
"""
    Used to generate synthetic data as an example.

    Writes two output files:

    * `<instance ID>_solution.json`: contains the synthetic data
    * `<instance ID>_stats.csv`: contains provenance information about the run

    The JSON file is, in turn, read by the a per-instance jupyter notebook
    available on the Portal to generate a plot of the data.
"""
import argparse
from typing import Any
import json
import csv
from time import time
from traceback import print_exc
import numpy as np

from ipsframework.resourceHelper import get_platform_info


def main(instance: str,
         alpha: float, L:float, T_final:float, Nx:int, Nt:int) -> dict[str, Any]:
    """ Generate synthetic data to emulate an actual simulation or complex
            calculation.

        As a side-effect it will save a plot to the current working directory with
        the name `solution.png`.

        :param instance: instance name
        :param alpha: thermal diffusivity
        :param L: domain length
        :param T_final: final time
        :param Nx: number of spatial grid points
        :param Nt: number of time steps
        :returns: x, y, where x is the steps and u the corresponding values
    """
    start = time()

    # Discretization
    dx = L / (Nx - 1)
    dt = T_final / Nt
    r = alpha * dt / (dx ** 2)

    # # Check stability condition for explicit method
    if r > 0.5:
        print("Warning: Stability condition r <= 0.5 is not met. "
              "Results may be inaccurate.")

    # Initial condition (e.g., a sine wave)
    x = np.linspace(0, L, Nx)
    u = np.sin(np.pi * x)

    # Boundary conditions (Dirichlet, e.g., u(0,t) = 0, u(L,t) = 0) These are
    # already handled by the initial setup of u=0 at boundaries if the
    # initial condition is 0 there. If non-zero, they would be set within the
    # time loop.

    # Time evolution
    for n in range(Nt):
        u_new = np.copy(u)  # Create a copy for updating
        for i in range(1, Nx - 1):
            u_new[i] = u[i] + r * (u[i + 1] - 2 * u[i] + u[i - 1])
        u = u_new



    # Save some per-component stats
    stats_fname = f'{instance}_stats.csv'
    run_env = get_platform_info()

    with open(stats_fname, 'w') as f:
        # Write run-time stats to a CSV as well as the runtime parameters
        # specific to this instance.
        writer = csv.writer(f)
        writer.writerow(
                ['instance', 'hostname', 'pid', 'core',
                 'affinity',
                 'alpha', 'L', 'T_final', 'Nx', 'Nt',
                 'start', 'end'])

        writer.writerow([instance, run_env['hostname'],
                         run_env['pid'], run_env['core_id'],
                         run_env['affinity'],
                         alpha, L, T_final, Nx, Nt,
                         start, time()])

    return {'x': x.tolist(), 'u': u.tolist()}



if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='Generate synthetic data to '
                                                     'emulate an actual simulation '
                                                     'or complex')
        parser.add_argument('--instance', type=str,
                            help='instance name')
        parser.add_argument('--alpha', type=float, default=1.0,)
        parser.add_argument('--L', type=float, default=1.0,)
        parser.add_argument('--T_final', type=float, default=1.0,)
        parser.add_argument('--Nx', type=int, default=100,)
        parser.add_argument('--Nt', type=int, default=100,)

        args = parser.parse_args()

        data = main(args.instance,
                    args.alpha, args.L, args.T_final, args.Nx, args.Nt)

        file_name = f'{args.instance}_solution.json'
        print(f'Writing to {file_name}')
        with open(file_name, 'w') as f:
            json.dump(data, f)

    except Exception as e:
        print(f'Encountered error: {e}')
        with open('gen_data_error.txt', 'w') as f:
            print(f'Encountered error: {e!s}', file=f)
        print_exc()
