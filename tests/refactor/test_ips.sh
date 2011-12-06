#!/bin/sh

source ../frameworkpath.py

###
##  Some initial setting up
#
if test -d test_basic_serial1_0; then
  /bin/rm -rf test_basic_serial1_0
fi
if test -e test_basic_serial1_0.zip ; then
  /bin/rm -f test_basic_serial1_0.zip
fi

touch file1  ofile1  ofile2  sfile1  sfile2

#-------------------------------------------------------
echo; echo; echo
echo "Testing runspace creation"
#-------------------------------------------------------
#${fsrc}/ips.py --create-runspace --simulation=basic_serial1.ips --sim_name=basic_foo
${fsrc}/ips.py --create-runspace --simulation=basic_foo1:b1.ips,basic_foo2:b2.ips --sim_name=basic_foo
#-------------------------------------------------------
exit
echo; echo; echo
echo "Testing run setup"
#-------------------------------------------------------
${fsrc}/ips.py --run-setup  --simulation=basic_serial1.ips
#-------------------------------------------------------
echo; echo; echo
echo "Testing running under ips"
#-------------------------------------------------------
${fsrc}/ips.py --run --simulation=basic_serial1.ips
exit
#
#-------------------------------------------------------
echo; echo; echo
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --clone=basicsim01  --simulation=basic_serial02
#-------------------------------------------------------
echo; echo; echo
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --run-setup --simulation=basicsim02
#-------------------------------------------------------
echo; echo; echo
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --run --simulation=basicsim02
