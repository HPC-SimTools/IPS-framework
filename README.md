# Integrated Plasma Simulator (IPS) Framework

The documentation can be found at https://ips-framework.readthedocs.io

Installation is available via pip:

```
python3 -m pip install ipsframework
```

or to install the latest development version from github:

```
python3 -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git
```

## Installing from source

```
python3 setup.py install
```

### Install in develop mode

```
python3 setup.py develop
```

## Running IPS

```
ips.py --help
ips.py --config=simulation.config --platform=platform.conf
```

## To run the tests (requires pytest)

```
python3 setup.py test
```

---
[![CI](https://github.com/HPC-SimTools/IPS-framework/workflows/CI/badge.svg)](https://github.com/HPC-SimTools/IPS-framework/actions)
[![codecov](https://codecov.io/gh/HPC-SimTools/IPS-framework/branch/master/graph/badge.svg)](https://codecov.io/gh/HPC-SimTools/IPS-framework)
[![Documentation Status](https://readthedocs.org/projects/ips-framework/badge/?version=latest)](https://ips-framework.readthedocs.io/en/latest/?badge=latest)
