#!/bin/sh
cd $(dirname "$0")
ips.py --config=parent.conf --platform=platform.conf --log=ips.log #--debug --verbose
