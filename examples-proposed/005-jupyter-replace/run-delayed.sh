#!/bin/sh
cd $(dirname "$0")
EXAMPLE_DELAY=true ips.py --config=sim.conf --platform=platform.conf --log=ips.log #--debug --verbose
