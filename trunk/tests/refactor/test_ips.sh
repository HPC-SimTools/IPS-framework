#!/bin/sh
ips --create-runspace --simulation=basicsim01 
ips --run-setup --simulation=basicsim01 
ips --run --simulation=basicsim01 
#
ips --clone=basicsim01 --simulation=basicsim02
ips --run-setup --simulation=basicsim02
ips --run --simulation=basicsim02
