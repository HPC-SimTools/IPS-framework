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
        'simulation_component_1': {
            'PARAMETER_A': [value1, value2, value3],
            'PARAMETER_B': [value1, value2, value3],
            'PARAMETER_C': [value1, value2, value3]
        },
        'simulation_component_2': {
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

Configuration Template
----------------------

The configuration template file should contain placeholder variables that will be substituted with actual values. Use ``?PARAMETER_NAME?`` syntax for placeholders:

.. code-block:: ini

    [GLOBAL]
    SIM_NAME = ensemble_?INSTANCE_ID?

    [physics_component]
    CLASS = PhysicsComponent
    DENSITY = ?DENSITY?
    TEMPERATURE = ?TEMPERATURE?
    MAGNETIC_FIELD = ?MAGNETIC_FIELD?

    [transport_component]
    CLASS = TransportComponent
    CHI_E = ?CHI_E?
    CHI_I = ?CHI_I?

Directory Structure
-------------------

The ensemble execution creates the following directory structure:

.. code-block::

    run_dir/
    ├── ensemble_member_001/
    │   ├── config.conf
    │   ├── work/
    │   └── simulation_results/
    ├── ensemble_member_002/
    │   ├── config.conf
    │   ├── work/
    │   └── simulation_results/
    └── ...

Each ensemble member runs in its own isolated directory with a unique configuration file generated from the template.

Resource Management
-------------------

The ensemble system uses Dask for distributed computing:

- **Nodes**: Each specified node runs one Dask worker
- **Cores**: Distributed among ensemble members based on ``cores_per_instance``
- **Memory**: Automatically managed by Dask scheduler
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
- Ensemble size is limited by available compute resources
- All ensemble members must use the same basic simulation structure
- Parameter substitution is limited to simple string replacement

See Also
--------

- :meth:`ServicesProxy.create_task_pool`: For managing large numbers of tasks
- :meth:`ServicesProxy.submit_tasks`: For distributed task execution
- :doc:`configuration`: For details on configuration file structure