# Integrated Plasma Simulator (IPS) Framework

IPS is an environment to orchestrate complex coupled simulation
workflows on parallel computers. The IPS is designed primarily for use
in a batch-processing environment, with a batch job typically
comprising a single invocation of the framework, calling the
individual physics codes many times as the simulation progresses.

The user documentation can be found at
https://ips-framework.readthedocs.io

Bug reports (including security bugs) and enhancement requests can be
made using [GitHub
issues](https://github.com/HPC-SimTools/IPS-framework/issues)

Alternatively the developers can be contacted at
[discussions](https://github.com/HPC-SimTools/IPS-framework/discussions)

## Contributing

Change requests can be made using [GitHub pull
request](https://github.com/HPC-SimTools/IPS-framework/pulls)

A guide for developing IPS-framework can be found at [Developer
Guide](https://ips-framework.readthedocs.io/en/latest/development.html)

## Installing IPS-framework:

The easiest way to install the latest version is from PyPI. For more
details see [Getting
Started](https://ips-framework.readthedocs.io/en/latest/getting_started/getting_started.html)

```
python -m pip install ipsframework
```

## Running IPS

See the [User
Guides](https://ips-framework.readthedocs.io/en/latest/user_guides/user_guides.html)
for detailed information on how to run IPS.

```
ips.py --help
ips.py --config=simulation.config --platform=platform.conf
```

---
[![CI](https://github.com/HPC-SimTools/IPS-framework/workflows/CI/badge.svg)](https://github.com/HPC-SimTools/IPS-framework/actions)
[![codecov](https://codecov.io/gh/HPC-SimTools/IPS-framework/branch/main/graph/badge.svg)](https://codecov.io/gh/HPC-SimTools/IPS-framework)
[![Documentation Status](https://readthedocs.org/projects/ips-framework/badge/?version=latest)](https://ips-framework.readthedocs.io/en/latest/?badge=latest)
[![CII Best Practices](https://bestpractices.coreinfrastructure.org/projects/4824/badge)](https://bestpractices.coreinfrastructure.org/projects/4824)
