Ensemble Simulations
====================

The IPS framework provides the ability to run ensemble simulations through the :meth:`ServicesProxy.run_ensemble` method. This feature allows you to execute multiple simulation instances with different parameter combinations in parallel using Dask for distributed computing.

Overview
--------

Ensemble simulations are useful when you need to:

- Perform parameter sweeps across multiple variables
- Run sensitivity analyses
- Execute Monte Carlo simulations
- Conduct uncertainty quantification studies

The ensemble functionality automatically generates configuration files for each simulation instance, distributes the workload across available compute nodes, and manages the execution of all ensemble members.

Method Signature
----------------

.. automethod:: ipsframework.services.ServicesProxy.run_ensemble

Parameters
----------

template : str
    Path to the configuration template file. This file should contain placeholder variables marked with ``?`` that will be replaced with actual values for each ensemble member.

variables : dict
    A nested dictionary structure where:

    - Keys are simulation component names
    - Values are dictionaries mapping parameter names to lists of values

    Each combination of parameter values will generate a separate ensemble member.

run_dir : str
    Base directory where ensemble simulations will be executed. Each ensemble member will run in its own subdirectory.

name : str
    Ensemble name or prefix used for generating unique directory and file names for each ensemble member.

num_nodes : int
    Total number of compute nodes to allocate for the ensemble runs. One Dask worker will be assigned to each node.

cores_per_instance : int, optional
    Number of CPU cores to allocate per ensemble instance. If not specified, cores will be distributed automatically.

Returns
-------

list of dict
    A list containing dictionaries that map created subdirectories to simulation names and their parameter combinations.

Variables Dictionary Structure
------------------------------

The ``variables`` parameter uses a specific nested dictionary structure:

.. code-block:: python

    variables = {
        'component_1': {
            'PARAMETER_A': [value1, value2, value3],
            'PARAMETER_B': [value1, value2, value3],
            'PARAMETER_C': [value1, value2, value3]
        },
        'component_2': {
            'PARAMETER_D': [value1, value2, value3],
            'PARAMETER_E': [value1, value2, value3]
        }
    }

Example Usage
-------------

Basic Parameter Sweep
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Define parameter combinations
    variables = {
        'physics_component': {
            'DENSITY': [1.0e19, 2.0e19, 3.0e19],
            'TEMPERATURE': [1000, 2000, 3000],
            'MAGNETIC_FIELD': [2.0, 3.0, 4.0]
        }
    }

    # Run ensemble
    results = services.run_ensemble(
        template='config_template.conf',
        variables=variables,
        run_dir='/scratch/ensemble_runs',
        name='parameter_sweep',
        num_nodes=4,
        cores_per_instance=8
    )

Multi-Component Ensemble
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    variables = {
        'transport_component': {
            'CHI_E': [0.5, 1.0, 1.5],
            'CHI_I': [0.3, 0.6, 0.9]
        },
        'heating_component': {
            'POWER': [5.0, 10.0, 15.0],
            'BEAM_ENERGY': [50, 75, 100]
        }
    }

    results = services.run_ensemble(
        template='multi_physics_template.conf',
        variables=variables,
        run_dir='/tmp/multi_component_ensemble',
        name='coupled_physics',
        num_nodes=8
    )


Creating Variables from CSV Files
---------------------------------

For convenience, the IPS framework provides the :func:`ipsframework.ipsutil.params_from_csv` utility function to generate the variables dictionary from a CSV file. This is particularly useful when working with parameter combinations exported from spreadsheets or generated programmatically.

Function Signature
~~~~~~~~~~~~~~~~~~

.. autofunction:: ipsframework.ipsutil.params_from_csv

CSV File Format
~~~~~~~~~~~~~~~

The CSV file should follow this structure:

- **Header row**: Column names in the format ``component_name:parameter_name``
- **Data rows**: Parameter values for each ensemble member

Example CSV file:

.. code-block:: text

    physics_comp:DENSITY, physics_comp:TEMPERATURE, transport_comp:CHI_E
    1.0e19, 1000, 0.5
    2.0e19, 2000, 1.0
    3.0e19, 3000, 1.5

This CSV format allows you to:

- Export parameter combinations directly from spreadsheet applications
- Generate files programmatically using pandas or other data processing tools
- Maintain parameter combinations in version control as plain text

Usage Example
~~~~~~~~~~~~~

.. code-block:: python

    from ipsframework.ipsutil import params_from_csv

    # Load parameters from CSV file
    variables = params_from_csv('ensemble_parameters.csv')

    # Run ensemble with CSV-generated parameters
    results = services.run_ensemble(
        template='config_template.conf',
        variables=variables,
        run_dir='/scratch/csv_ensemble',
        name='csv_parameter_sweep',
        num_nodes=4
    )

The CSV file above would generate the equivalent variables dictionary:

.. code-block:: python

    variables = {
        'physics_comp': {
            'DENSITY': ['1.0e19', '2.0e19', '3.0e19'],
            'TEMPERATURE': ['1000', '2000', '3000']
        },
        'transport_comp': {
            'CHI_E': ['0.5', '1.0', '1.5']
        }
    }

Integration with Data Analysis Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CSV format integrates well with common data analysis workflows:

**Pandas DataFrame export:**

.. code-block:: python

    import pandas as pd

    # Create parameter combinations
    df = pd.DataFrame({
        'physics_comp:DENSITY': [1.0e19, 2.0e19, 3.0e19],
        'physics_comp:TEMPERATURE': [1000, 2000, 3000],
        'transport_comp:CHI_E': [0.5, 1.0, 1.5]
    })

    # Export to CSV for ensemble use
    df.to_csv('parameters.csv', index=False)

    # Load in IPS
    variables = params_from_csv('parameters.csv')

**Parameter space generation:**

.. code-block:: python

    import itertools
    import csv

    # Generate all combinations of parameters
    densities = [1.0e19, 2.0e19, 3.0e19]
    temperatures = [1000, 2000, 3000]
    chi_values = [0.5, 1.0, 1.5]

    with open('full_factorial.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['physics_comp:DENSITY', 'physics_comp:TEMPERATURE', 'transport_comp:CHI_E'])
        for combo in itertools.product(densities, temperatures, chi_values):
            writer.writerow(combo)

Template Configuration Template File
------------------------------------

The configuration template file should contain placeholder variables that will be substituted with actual values.
Use ``?`` syntax for placeholders.  It is otherwise a standard IPS configuration file.:

.. code-block:: ini

    SIM_ROOT = $PWD
    SIM_NAME = ensemble_instance
    SIMULATION_MODE = NORMAL
    LOG_LEVEL = INFO
    LOG_FILE  = instance_run.log

    [PORTS]
    NAMES = DRIVER, PHYSICS, TRANSPORT

    [DRIVER]
        IMPLEMENTATION = driver

    [PHYSICS]
        IMPLEMENTATION = physics_component

    [TRANSPORT]
        IMPLEMENTATION = transport_component

    [driver]
        CLASS = driver
        SUB_CLASS =
        NAME = instance_driver
        SCRIPT = /my/bin/path/instance_driver.py
        NPROC = 1
        INPUT_FILES =
        OUTPUT_FILES =
        RESTART_FILES =

    [physics_component]
        BIN_PATH = /my/bin/path
        CLASS = workers
        SUB_CLASS =
        NAME = physics_comp
        SCRIPT = ${BIN_PATH}/physics_comp.py
        NPROC = 1
        INPUT_FILES =
        OUTPUT_FILES =
        RESTART_FILES =
        POWER = ?
        BEAM_ENERGY = ?
        CHI_I = ?

    [transport_component]
        BIN_PATH = /my/bin/path
        CLASS = workers
        SUB_CLASS =
        NAME = transport_comp
        SCRIPT = ${BIN_PATH}/transport_comp.py
        NPROC = 1
        INPUT_FILES =
        OUTPUT_FILES =
        RESTART_FILES =
        DENSITY = ?
        TEMPERATURE = ?


Directory Structure
-------------------

The ensemble execution creates something like the following directory structure:

.. code-block::

    run_dir/
    ├── MY_INSTANCE_0
    │ ├── MY_INSTANCE_0.config
    │ ├── MY_INSTANCE_0.log
    │ ├── MY_INSTANCE_0_platform.config
    │ ├── resource_usage
    │ ├── simulation_setup
    │ │   ├── physics_comp.py
    │ │   ├── transport_comp.py
    │ │   └── instance_driver.py
    │ └── work
    │     ├── driver__instance_driver_1
    │     ├── FWK_COMP_runspaceInitComponent_4
    │     ├── workers__physics_comp_2
    │     │   └── output.csv
    │     └── workers__transport_comp_3
    │         └── output.csv
    └── ...

Each ensemble member runs in its own isolated directory, as shown above, with a
unique configuration file generated from the template.

Resource Management
-------------------

The ensemble system uses Dask for distributed computing:

- **Nodes**: Each specified node runs one Dask worker
- **Cores**: Distributed among ensemble members based on ``cores_per_instance``
- **Memory**: Automatically managed by Dask scheduler and the underlying cluster job scheduler (e.g., SLURM, PBS)
- **Load Balancing**: Dask handles work distribution and load balancing

Best Practices
--------------

- **Template Design**: Create templates that are flexible and cover all variable parameters needed for your ensemble.

- **Resource Planning**: Consider the total computational requirements when specifying ``num_nodes`` and ``cores_per_instance``.

- **Parameter Ranges**: Choose parameter ranges that provide meaningful coverage of your parameter space.

- **Output Management**: Plan for sufficient storage space as ensembles can generate large amounts of output data.

- **Monitoring**: Use the IPS monitoring capabilities to track ensemble progress and identify failed runs.

Error Handling
--------------

The ensemble system provides robust error handling:

- Individual ensemble member failures don't stop the entire ensemble
- Failed runs are logged and can be identified in the results
- Resource allocation errors are reported with detailed messages
- Configuration template errors are caught before execution begins

Limitations
-----------

- The method signature indicates ``cores_per_instance`` is not yet fully implemented
- Parameter substitution is limited to simple string replacement

See Also
--------

- :meth:`ServicesProxy.create_task_pool`: For managing large numbers of tasks
- :meth:`ServicesProxy.submit_tasks`: For distributed task execution
