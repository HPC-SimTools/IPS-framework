# An example ensemble simulation for aggregated computing

This example demonstrates how to set up an ensemble simulation in IPS that 
performs aggregated computing across multiple ensemble instances. Each ensemble 
instance runs a component for ${COMPUTE} that reports values local to the 
instance, but that is then aggregated at the top-level after the instances
have finished.

Note that there will be Dask related errors and warnings at the end that can be
ignored.  These are due to Dask not having a clean shutdown.

## Contents

* `driver.py` -- top-level driver
* `instance_component.py` -- component worker code
* `instance_driver.py` -- component driver code

* `ensemble.conf` -- top-level configuration file
* `platform.conf` -- platform configuration file
* `template.conf` -- ensemble instance configuration file


## Instructions

To run the code, run:

```bash
PORTAL_API_KEY=changeme ips.py --platform platform.conf --simulation ensemble.conf
```

Depending on the web portal instance you want to connect to, you will need to 
change `PORTAL_API_KEY` in the run command and `PORTAL_URL` in the 
`ensemble.conf` file.
