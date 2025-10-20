#!/bin/bash
#
# Set up the IPS ensemble example run.  Note that you must have a setup
# python environment on Perlmutter in which IPS is already installed for
# this example to work.
#SBATCH --account=atom # REPLACE WITH YOUR PROJECT ID
#SBATCH --constraint=cpu
#SBATCH --nodes=2
#SBATCH --time=30
#SBATCH --qos=regular


module load PrgEnv-gnu openmpi python
conda activate ips


ips.py -v --debug --log=${SLURM_JOBID}_full.log \
  --simulation=ensemble.conf --platform=perlmutter.conf 2>&1 | tee ${SLURM_JOBID}_fullrun.log

