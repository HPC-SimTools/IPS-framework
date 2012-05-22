#!/bin/sh

source ../frameworkpath.py

echo
echo
echo
#${fsrc}/ips.py --all --component=generic,conflicting --simulation=hello_world.ips
${fsrc}/ips.py --all --simulation=hello_world.ips

