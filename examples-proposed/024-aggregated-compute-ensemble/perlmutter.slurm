#!/bin/bash
#
# Set up the IPS ensemble example run.  Note that you must have a setup
# python environment on Perlmutter in which IPS is already installed for
# this example to work.  In this case, the conda environment is named "ips", but you're
# free to create your own environment with a different name; but, be sure to
# change the "conda activate" line below accordingly if you do so.
#
#SBATCH --account=atom # REPLACE "atom" WITH YOUR PROJECT ID
#SBATCH --constraint=cpu
#SBATCH --nodes=1
#SBATCH --time=5
#SBATCH -p debug
module purge
# ensure we're not accidentally picking up this being set in the environment by the user, which can cause problems
# with the MPI libraries.
unset LD_LIBRARY_PATH
module load PrgEnv-gnu openmpi python

# Again, this assumes that there exists a conda environment named "ips".
conda activate ips

# Set the API key and portal URL
source /global/common/software/atom/ips-portal/credentials/ips-portal-development

# The 2>&1 binds stderr to stdout so that both are captured in the tee log file.  The
# `tee` command allows you to see the output on the terminal as well as save it.
ips.py --simulation=ensemble.conf --platform=platform.conf \
    2>&1 | tee ${SLURM_JOBID}_ips.log

