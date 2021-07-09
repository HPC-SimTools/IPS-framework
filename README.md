# Integrated Plasma Simulator (IPS) Framework

The documentation can be found at https://ips-framework.readthedocs.io

Installation is available via pip:

```
python -m pip install ipsframework
```

or to install the latest development version from github:

```
python -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git
```

## Installing from source

```
python -m pip install .
```

### Install in develop mode

```
python -m pip install -e .
```

## Running IPS

```
ips.py --help
ips.py --config=simulation.config --platform=platform.conf
```

## To run the tests

Requires `pytest` and `psutil`. Optional dependencies are
`dask`/`distributed` and `mpirun`, to run all tests.

```
python -m pytest
```

To run test showing code coverage, install `pytest-cov` and run

```
python -m pytest --cov
```

---
[![CI](https://github.com/HPC-SimTools/IPS-framework/workflows/CI/badge.svg)](https://github.com/HPC-SimTools/IPS-framework/actions)
[![codecov](https://codecov.io/gh/HPC-SimTools/IPS-framework/branch/main/graph/badge.svg)](https://codecov.io/gh/HPC-SimTools/IPS-framework)
[![Documentation Status](https://readthedocs.org/projects/ips-framework/badge/?version=latest)](https://ips-framework.readthedocs.io/en/latest/?badge=latest)
