#! /bin/bash
#PBS -A  m876 
#PBS -N model_sim_run
#PBS -m e
#PBS -j oe
#PBS -l walltime=0:12:00
#PBS -l mppwidth=8
#PBS -q debug
#PBS -S /bin/bash
#PBS -o myout.txt
#PBS -e myerr.txt

cd $PBS_O_WORKDIR
umask=0222
$SCRATCH/ips/utilities/dakota_studies/model_sim_mcmd_param_study/dakota_wrapper.sh $SCRATCH/ips/utilities/dakota_studies/model_sim_mcmd_param_study/model_sim_mcmd_sveta.conf $SCRATCH/ips/utilities/dakota_studies/model_sim_mcmd_param_study/dakota_ips.in
