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

### Bash 
To run the code, run:

```bash
ips.py --platform platform.conf --simulation ensemble.conf
```

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

Runnming the example will generate log files in the current directory.  However,
the ensembles will be found in the `ENSEMBLES` directory, which was specified
via SIM_ROOT in `ensemble.conf`.  The output inside `ENSEMBLES` will look like:

```
ENSEMBLES/
├── ensemble.conf
├── perlmutter.conf
├── resource_usage
├── simulation_setup
│   └── driver.py
└── work
    ├── DRIVER__EnsembleDriver_1
    │   ├── INSTANCE_0
    │   │   ├── INSTANCE_0.config
    │   │   ├── INSTANCE_0.log
    │   │   ├── INSTANCE_0_platform.config
    │   │   ├── INSTANCE_0_run.log
    │   │   ├── resource_usage
    │   │   ├── simpleensemble_a18849a2-cb31-4c73-8417-d01c57a69339_INSTANCE__ensemble_task_pool_tcp12855731439951.json
    │   │   ├── simulation_setup
    │   │   │   ├── instance_component.py
    │   │   │   └── instance_driver.py
    │   │   └── work
    │   │       ├── DRIVER__InstanceDriver_1
    │   │       ├── FWK_COMP_runspaceInitComponent_3
    │   │       └── WORKER__InstanceComponent_2
    │   │           └── stats.csv
    │   ├── INSTANCE_1
    │   │   ├── INSTANCE_1.config
    │   │   ├── INSTANCE_1.log
    │   │   ├── INSTANCE_1_platform.config
    │   │   ├── INSTANCE_1_run.log
    │   │   ├── resource_usage
    │   │   ├── simpleensemble_a18849a2-cb31-4c73-8417-d01c57a69339_INSTANCE__ensemble_task_pool_tcp12855731439951.json
    │   │   ├── simulation_setup
    │   │   │   ├── instance_component.py
    │   │   │   └── instance_driver.py
    │   │   └── work
    │   │       ├── DRIVER__InstanceDriver_1
    │   │       ├── FWK_COMP_runspaceInitComponent_3
    │   │       └── WORKER__InstanceComponent_2
    │   │           └── stats.csv
    │   ├── INSTANCE_2
    │   │   ├── INSTANCE_2.config
    │   │   ├── INSTANCE_2.log
    │   │   ├── INSTANCE_2_platform.config
    │   │   ├── INSTANCE_2_run.log
    │   │   ├── resource_usage
    │   │   ├── simpleensemble_a18849a2-cb31-4c73-8417-d01c57a69339_INSTANCE__ensemble_task_pool_tcp12855731439951.json
    │   │   ├── simulation_setup
    │   │   │   ├── instance_component.py
    │   │   │   └── instance_driver.py
    │   │   └── work
```

Observe that the instances have their own directories under
`work/DRIVER__EnsembleDriver_1/`
and that they follow the naming pattern of `INSTANCE_<instance_id>`; this 
pattern was given with the `name` parameter in the `run_ensemble()` call 
found in `driver.py`, which is the top-level driving component.  Inside each
instance directory is the output from the IPS run for that instance.  Further note that inside the `work` directory for each instance under 
`WORKER__InstanceComponent_2` is a `stats.csv` file that contains the output 
from that instance's component.  This file contains the instance name (e.g., 
`INSTANCE_0`), the IPS executable script, the hostname
where the component ran, the process id, core ID, and the start and end times 
that component ran.  Note that all three components ran at about the same time
on different cores.

You can conveniently see all the `stats.csv` files for all instances by running 
the following command:

```bash
find . -name stats.csv | xargs cat
```

## Next example

The next example is 021-ensembles-from-CSV, which shows how to run an ensemble
where the instance parameters are read from a CSV file.

