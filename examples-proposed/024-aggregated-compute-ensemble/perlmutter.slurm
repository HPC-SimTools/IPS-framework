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

module load PrgEnv-gnu python

# Again, this assumes that there exists a conda environment named "ips".
conda activate ips

# You MUST load openmpi AFTER activating the conda environment.  This is because
# the conda environment may have its own MPI libraries, and loading openmpi after
# activating the conda environment ensures that the correct MPI libraries are used.
# If you load openmpi before activating the conda environment, you may end up with
# a mismatch of MPI libraries, which can lead to runtime errors.
module load openmpi

# Set the API key and portal URL
source /global/common/software/atom/ips-portal/credentials/ips-portal-development

# The 2>&1 binds stderr to stdout so that both are captured in the tee log file.  The
# `tee` command allows you to see the output on the terminal as well as save it.
ips.py --simulation=ensemble.conf --platform=perlmutter.conf \
    2>&1 | tee ${SLURM_JOBID}_ips.log

