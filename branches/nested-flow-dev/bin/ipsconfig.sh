#!/bin/sh

#------------------------------------------------------------------
# Script: ipsconfig.sh.sh		Authors: Scott Kruger
# Usage: ipsconfig.sh.sh
# Description:  Create a configure script for configuring ips
#   This uses host_config.sh in the same directory to determine
#   standard defaults used by the swim project.  Done in shell script to
#   be fast
#------------------------------------------------------------------
#------------------------------------------------------------------
# Grab the host info
#------------------------------------------------------------------
topscriptdir=`dirname $0`
if test -e $topscriptdir/host_config.sh; then
	source $topscriptdir/host_config.sh
else
	echo "Cannot find host_config.sh.  Exiting.";  exit
fi
host_info
ipsdir=`dirname $topscriptdir`

#------------------------------------------------------------------
# Append to line
#------------------------------------------------------------------
deref() {
        eval echo $`echo $1`
}
append_line () {
    line=$1
    var=$2
    val=`deref $var`
    if test -n "$val"; then 
          echo $line"   -D${var}=${val} \!"
    else
          # If not specified, just comment out to show the user how to
          # specify it.
          echo $line
          echo "#   -D${var}=@${var}@ \ " >> configtemp.sh
    fi
}
#------------------------------------------------------------------
# Create config.sh
#------------------------------------------------------------------
create_config () {
  rm -f configtemp.sh
  t="cmake \!"
  t=`append_line "$t" CMAKE_INSTALL_PREFIX`
  t=`append_line "$t" MPIRUN`
  t=`append_line "$t" NODE_DETECTION`
  t=`append_line "$t" CORES_PER_NODE`
  t=`append_line "$t" SOCKETS_PER_NODE`
  t=`append_line "$t" NODE_ALLOCATION_MODE`
  t=`append_line "$t" PORTAL_URL`
  t=`append_line "$t" RUNID_URL`
  t=`append_line "$t" BIN_PATH`
  t=`append_line "$t" PHYS_BIN_ROOT`
  t=`append_line "$t" INPUT_DIR`
  t=`append_line "$t" DATA_ROOT`
  t=$t"${ipsdir}"
  echo $t | tr ! '\012' > config.sh
  cat configtemp.sh >> config.sh
  rm -f configtemp.sh
  chmod u+rx config.sh
}	


#------------------------------------------------------------------
# START CODE EXECUTION HERE
#> set(PORTAL_URL      "http://swim.gat.com:8080/monitor" CACHE STRING "URL of portal")
#> set(RUNID_URL       "http://swim.gat.com:4040/runid.esp" CACHE STRING "URL of runId")
#> set(MPIRUN          "mpiexec" CACHE STRING "Executable of mpi to submit jobs")
#> set(NODE_DETECTION  "manual" CACHE STRING "Resource detection method")
#> set(CORES_PER_NODE  "1" CACHE STRING "Cores per node")
#> set(SOCKETS_PER_NODE  "1" CACHE STRING "Sockets per node")
#> set(NODE_ALLOCATION_MODE "shared" CACHE STRING "node allocation")
#------------------
#> set(BIN_PATH   "${CMAKE_BINARY_DIR}" CACHE PATH "Location of component scripts")
#> set(PHYS_BIN_ROOT   "${CMAKE_BINARY_DIR}" CACHE PATH "Location of physics binaries")
#> set(INPUT_DIR  "${CMAKE_INSTALL_DIR}/share" CACHE PATH "Location of component input files")
#> set(DATA_ROOT  "${CMAKE_INSTALL_DIR}/share" CACHE PATH "Location of physics data files")
#> set(CONTAINER_FILE_EXT          "ctz" CACHE STRING "File extension for container file")
#------------------------------------------------------------------
#clear; echo; echo

echo "Edit config.sh to change."
echo "Execute config.sh to try it out"
create_config

exit
