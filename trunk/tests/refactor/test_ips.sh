#!/bin/sh

source ../frameworkpath.py

###
##  Some initial setting up
#
if test -d test_basic_serial1_0; then
  /bin/rm -rf test_basic_serial1_0
fi
if test -e test_basic_serial1_0.ctz ; then
  /bin/rm -f test_basic_serial1_0.ctz
fi
if test -d basic_serial02; then
  /bin/rm -rf test_basic_serial1_0
fi
if test -e basic_serial02.ctz ; then
  /bin/rm -f basic_serial02.ctz
fi

touch file1  ofile1  ofile2  sfile1  sfile2

#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing runspace creation"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips.py --create-runspace --simulation=b1.ips 

#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing run setup"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips.py --run-setup --simulation=b1.ips

#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing running under ips"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips.py --run --simulation=b1.ips

echo "-------------------------------------------------------"
echo "Testing all with two ips files and two names"
echo "-------------------------------------------------------"
${fsrc}/ips.py --create-runspace --run-setup --run --simulation=b1.ips,b2.ips --sim_name=b,c

exit;
#-------------------------------------------------------------
#  The above is similar to the above except we first
#  start off by using the container file above to create 
#  the run space using the --clone command.  We next
#  use the --sim_name construct throughout to never 
#  explicitly refer to the ips file: we let the initial
#  ips.py pre-processing handle that.  This mimics more
#  closely what the composer needs.
#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing runspace creation using --clone"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips.py --clone=test_basic_serial1_0.ctz  --sim_name=basic_serial02
#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing run_setup from cloned directory"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips.py --run-setup  --sim_name=basic_serial02
#-------------------------------------------------------------
echo; echo; echo
echo "-------------------------------------------------------"
echo "Testing run from cloned directory"
echo "-------------------------------------------------------"
#-------------------------------------------------------------
${fsrc}/ips.py --run   --sim_name=basic_serial02
