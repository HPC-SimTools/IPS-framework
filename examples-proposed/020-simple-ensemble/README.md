# Simple ensemble example 

This shows how to run an ensemble for three instances.

Note that there will be Dask related errors and warnings at the end that can be
ignored.  These are due to Dask not having a clean shutdown.

## Contents

* `__init__.py` -- empty python init file
* `driver.py` -- top-level driver
* `instance_component.py` -- component worker code
* `instance_driver.py` -- component driver code

* `ensemble.conf` -- top-level configuration file
* `platform.conf` -- platform configuration file
* `template.conf` -- ensemble instance configuration file


## Instructions

To run the code, run:

```bash
ips.py --platform platform.conf --simulation ensemble.conf
```