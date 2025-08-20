#!/bin/sh
set -e
cd "$(dirname "$0")"
PORTAL_API_KEY=${PORTAL_API_KEY:-changeme} ips.py --config=sim.conf --platform=platform.conf --log=ips.log #--debug --verbose
