# Ensemble instances that launch tasks

This shows an example of launching tasks from within ensemble instances. In 
particular, each ensemble instance launches a task that runs a simple Python script
that prints out the parameters passed to it and shows the run-time information
such as the MPI rank, hostname, process ID, core affinities, start and stop 
times.

One difference from the 020 and 021 examples is that one of the instance 
parameters, B, will be used to control how long the task runs via a call to
time.sleep().


## Contents

* `__init__.py` -- empty python init file
* `driver.py` -- top-level driver
* `instance_component.py` -- component worker code
* `instance_driver.py` -- component driver code

* `ensemble.conf` -- top-level configuration file
* `platform.conf` -- platform configuration file
* `perlmutter.conf` -- Perlmutter platform configuration file
* `template.conf` -- ensemble instance configuration file

* `perlmutter.slurm` -- SLURM submission script for Perlmutter


## Instructions

### Bash 
To run the code, run:

```bash
ips.py --platform platform.conf --simulation ensemble.conf
```
__NOTE__: disable Global Protect VPN if you are using it, as it can interfere 
with Dask.

### Perlmutter

To run on Perlmutter, follow these steps

1. Create a conda environment 
2. Install IPS into the conda environment
3. Modify `perlmutter.slurm` to point to your conda environment and to use 
   your project ID
4. Run the example using the following command from within the directory:
    ```bash
     sbatch perlmutter.slurm
    ```


## Output

The output is the similar to the `020-simple-ensemble` example in that the 
instances write statistics to `stats.csv`, but there
is more information written, such as MPI rank and core affinities.
