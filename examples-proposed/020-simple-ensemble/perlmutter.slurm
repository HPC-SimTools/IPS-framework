#!/bin/bash
#
# Set up the IPS ensemble example run.  Note that you must have a setup
# python environment on Perlmutter in which IPS is already installed for
# this example to work.  In this case, the conda environment is named "ips", but you're
# free to create your own environment with a different name; but, be sure to
# change the "conda activate" line below accordingly if you do so.
#
#SBATCH --account=atom # REPLACE WITH YOUR PROJECT ID
#SBATCH --constraint=cpu
#SBATCH --nodes=1
#SBATCH --time=5
#SBATCH -p debug

module load PrgEnv-gnu openmpi python

# Again, this assumes that there exists a conda environment named "ips".
conda activate ips

ips.py -v --debug --log=${SLURM_JOBID}_full.log \
  --simulation=ensemble.conf --platform=perlmutter.conf 2>&1 | tee ${SLURM_JOBID}_ips.log

