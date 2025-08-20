# Task pool synchronous

This is an example which uses `dask`, an optional dependency. 

Dask enables you to run multiple jobs in parallel. In this example, three different "sleep 1" commands are executed (one via subprocess and two via Python methods) but will all execute simultaneously. Try adding multiple tasks!

## Instructions

This example uses the script syntax, so to run it you only need to be in an environment where the ipsframework itself has been installed.

You will also need to have `dask` installed for this example.

To run the code, run:

```bash
ips.py --config=dask_sim.config --platform=platform.conf
```
