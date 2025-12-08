#!/usr/bin/env python3
"""
    Used to generate synthetic data as an example.
"""
import argparse
from typing import Any
import json
import numpy as np
import matplotlib.pyplot as plt


def main(alpha: float, L:float, T_final:float, Nx:int, Nt:int) -> dict[str, Any]:
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



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate synthetic data to '
                                                 'emulate an actual simulation or complex')
    parser.add_argument('--alpha', type=float, default=1.0,)
    parser.add_argument('--L', type=float, default=1.0,)
    parser.add_argument('--T_final', type=float, default=1.0,)
    parser.add_argument('--Nx', type=int, default=100,)
    parser.add_argument('--Nt', type=int, default=100,)

    args = parser.parse_args()

    data = main(args.alpha, args.L, args.T_final, args.Nx, args.Nt)

    with open('solution.json', 'w') as f:
        json.dump(data, f)
