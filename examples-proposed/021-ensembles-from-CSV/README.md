# Ensembles with variables from CSV files

This example shows how to run an ensemble of IPS simulations
where each instance uses different parameter values read from CSV files.


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
