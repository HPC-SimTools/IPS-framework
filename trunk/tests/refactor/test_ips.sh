#!/bin/sh
source ../frameworkpath.py
if test -d test_basic_serial1_0; then
  /bin/rm -rf test_basic_serial1_0
fi
#-------------------------------------------------------
echo; echo; echo
echo "Testing runspace creation"
#-------------------------------------------------------
${fsrc}/ips.py --create-runspace --simulation=basic_serial1.ips
#-------------------------------------------------------
echo; echo; echo
echo "Testing run setup"
#-------------------------------------------------------
${fsrc}/ips.py --run-setup  --simulation=basic_serial1.ips
exit
#-------------------------------------------------------
echo; echo; echo
echo "Testing running under ips"
#-------------------------------------------------------
${fsrc}/ips.py --run --simulation=basic_serial1.ips
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
