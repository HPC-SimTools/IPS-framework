#!/bin/sh
source ../frameworkpath.py
if test -d test_basic_serial1_0; then
  /bin/rm -rf test_basic_serial1_0
fi
#-------------------------------------------------------
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --create-runspace --simulation=basic_serial1.ips
exit
#-------------------------------------------------------
echo "Testing run setup"
#-------------------------------------------------------
${fsrc}/ips.py --run-setup --simulation=basicsim01 
#-------------------------------------------------------
echo "Testing running under ips"
#-------------------------------------------------------
${fsrc}/ips.py --run --simulation=basicsim01 
#
#-------------------------------------------------------
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --clone=basicsim01 --simulation=basicsim02
#-------------------------------------------------------
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --run-setup --simulation=basicsim02
#-------------------------------------------------------
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --run --simulation=basicsim02
