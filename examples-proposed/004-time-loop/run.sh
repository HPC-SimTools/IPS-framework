#!/bin/sh
PYTHONPATH=$(dirname "$0") PSCRATCH=${PSCRATCH:-/tmp} ips.py --config=sim.conf --platform=platform.conf --log=ips.log #--debug --verbose
