#! /bin/bash

#Are we in the correct directory?
#This must be run from the directory where it exists.
if [ ! -e dakota_wrapper.sh ]; then
  echo "Run.sh must be run in the same directory as dakota_wrapper.sh."
  echo "Exiting."
  exit -1
fi

#clean up from any previous run
rm -rf parameter_study

#Start the run
#first parameter is ips config file
#second parameter is dakota config file
./dakota_wrapper.sh model_sim_mcmd_sveta.conf dakota_ips.in
