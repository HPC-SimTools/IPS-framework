# Simple ensemble example 

This shows how to run an ensemble for three instances and how to save ensemble 
instances to an IPS Portal instance.  It also demonstrates using a Jupyter
notebook to read aggregate statistics from all the ensembles as found in
`./input_dir/notebook.ipynb`.

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

* `input_dir/notebook.ipynb` -- example notebook to read all ensemble 
  instance data for analytics


## Instructions

To run the code, run:

```bash
PORTAL_API_KEY=changeme ips.py --platform platform.conf --simulation ensemble.conf
```

Depending on the web portal instance you want to connect to, you will need to change `PORTAL_API_KEY` in the run command and `PORTAL_URL` in the `ensemble.conf` file.
