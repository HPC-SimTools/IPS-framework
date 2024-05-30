rm -rf sim
PYTHONPATH=$PWD ips.py --config=sim.conf --platform=platform.conf --log=ips.log #--debug --verbose
