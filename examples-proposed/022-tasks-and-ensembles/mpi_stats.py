#!/usr/bin/env python3
""" Echoes the MPI rank and size of the communicator, the hostname, the PID,
    affinity, and the number of cores. Also sleeps for a specified amount of time.
"""
import argparse
import csv
import sys

from mpi4py import MPI
from time import sleep, time

import os
import socket

try:
    import psutil
except ImportError:
    psutil = None

if __name__ == '__main__':
    start = time()

    parser = argparse.ArgumentParser(description='MPI stats')
    parser.add_argument('-i', '--id', type=str,
                        default=str(os.getpid()),
                        help='Task ID')
    parser.add_argument('-s', '--sleep',
                        default=5.0, type=float,
                        help='Sleep time in seconds')
    parser.add_argument('-o', '--output', type=str,
                        default=None, help='Output CSV file')

    args = parser.parse_args()

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    hostname = socket.gethostname()
    pid = os.getpid()

    if psutil:
        p = psutil.Process(pid)
        if hasattr(p, 'cpu_affinity'):
            affinity = p.cpu_affinity()
            n_cores = len(affinity)
        else:
            affinity = None
            n_cores = psutil.cpu_count()
    else:
        affinity = None
        n_cores = os.cpu_count()  # fallback

    print(f"Rank {rank} of {size} in task {args.id} on {hostname} "
          f"(pid {pid}) affinity {affinity!s} n_cores {n_cores} ")

    if args.sleep > 0:
        print(f"Task {args.id} sleeping {args.sleep} seconds...")
        sleep(args.sleep)

    if args.output is not None:
        with open(args.output, 'w', newline='') as csvfile:
            fieldnames = ['i', 'hostname', 'rank', 'size', 'pid', 'n_cores', 'affinity', 's', 'start', 'end']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            writer.writerow({'i': args.id, 'hostname': hostname,
                             'rank': rank, 'size': size, 'pid': pid,
                             'n_cores': n_cores, 'affinity': str(affinity), 's': args.sleep,
                             'start': start, 'end': time()})

    sys.exit(0)
