#!/usr/bin/env python3
"""
Component to be stepped in instance
"""

import csv
import itertools
import json
import sys
from time import time
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

from ipsframework import Component
from ipsframework.resourceHelper import get_platform_info


def generate_synthetic_data(alpha: float, L:float, T_final:float, Nx:int, Nt:int) -> dict[str, Any]:
    """ Generate synthetic data to emulate an actual simulation or complex
        calculation.

    As a side-effect it will save a plot to the current working directory with
    the name `solution.png`.

    :param alpha: thermal diffusivity
    :param L: domain length
    :param T_final: final time
    :param Nx: number of spatial grid points
    :param Nt: number of time steps
    :returns: x, y, where x is the steps and u the corresponding values
    """
    # Discretization
    dx = L / (Nx - 1)
    dt = T_final / Nt
    r = alpha * dt / (dx ** 2)
    #
    # # Check stability condition for explicit method
    if r > 0.5:
        print("Warning: Stability condition r <= 0.5 is not met. "
              "Results may be inaccurate.")

    # Initialize solution array
    u = np.zeros(Nx)

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

    # Plotting the result
    plt.plot(x, u)
    plt.xlabel("Position (x)")
    plt.ylabel("Temperature (u)")
    plt.title("Solution of 1D Heat Equation")
    plt.grid(True)
    plt.savefig("solution.png")

    return {'x': x.tolist(), 'u': u.tolist()}


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

        # generate some fake data and save it
        data_fname = f'generated_{timestamp}.json'
        data = generate_synthetic_data(float(self.alpha),
                                       float(self.L),
                                       float(self.T_final),
                                       int(self.Nx),
                                       int(self.Nt))
        with open(data_fname, 'w') as fd:
            json.dump(data, fd)

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
