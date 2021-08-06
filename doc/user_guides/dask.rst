Dask
====

The ability to use `Dask <https://dask.org>`_ for task pool scheduling
has been added and can be used by setting ``use_dask=True`` in
:meth:`~ipsframework.services.ServicesProxy.submit_tasks`.

You can decide how many nodes to use by setting ``dask_nodes``,  one Dask
worker will be created on every node, Dask will always use an entire
node, using all cores on the node.

The workflow added to IPS using Dask allows for more than just running
binary executables, you can run python functions and class methods.

An example showing this is the following, where we are adding an
executable (in this case :download:`sleep <../examples/dask/sleep>`),
a function that sleeps (``myFun``) and a method that sleeps
(``myMethod``) respectively to a task pool and submitting the task
pool with ``self.services.submit_tasks('pool', use_dask=True)``.

The :download:`driver.py <../examples/dask/driver.py>` in the most
simplest form would be

.. literalinclude:: ../examples/dask/driver.py

And the :download:`dask_worker.py <../examples/dask/dask_worker.py>`
is

.. literalinclude:: ../examples/dask/dask_worker.py

A simple config to run this is, :download:`dask_sim.config <../examples/dask/dask_sim.config>`

.. literalinclude:: ../examples/dask/dask_sim.config
   :language: text

This is executed with ``ips.py --config dask_sim.config --platform
platform.conf`` and the output shows each different task type
executing:

.. code-block:: text

  ...
  ret_val = 3
  myFun(0.5)
  myMethod(0.5)
  /bin/sleep 0.5
  exit_status =  {'binary': 0, 'method': 0, 'function': 0}
  ...

The output simulation log includes the start and end time of each task
with in the pool with the elapsed time as expected, a trimmed JSON
simulation log is shown:

.. literalinclude::  ../examples/dask/simulation_log.json
   :language: JSON


Running dask in shifter
-----------------------

`Shifter
<https://www.nersc.gov/research-and-development/user-defined-images>`_
is a resource for running docker containers on HPC. Documentation can
be found `here
<https://docs.nersc.gov/development/shifter/how-to-use>`_.

An option `use_shifter` has been added to
:meth:`~ipsframework.services.ServicesProxy.submit_tasks` that will
run the Dask scheduler and workers run inside the shifter container.

You will need to match the versions of Dask within the shifter
container to the version running outside. This is because the Dask
scheduler and workers run inside the container while IPS has the sk
client outside.

As an example would be using the module
``python/3.8-anaconda-2020.11`` and the docker image
``continuumio/anaconda3:2020.11`` which will have the same
environment.

You will need to have IPS installed in the conda environment
``python -m pip install ipsframework``. IPS is not required inside the
shifter container, only the Dask scheduler and workers are running
inside.

To pull down the docker into shifter run:

.. code-block:: bash

   shifterimg pull continuumio/anaconda3:2020.11

You can entry the shifter container and check it's contents with:

.. code-block:: bash

   shifter --image=continuumio/anaconda3:2020.11 /bin/bash

You batch script should then look like:

.. code-block:: bash

   #!/bin/bash
   ...
   #SBATCH --image=continuumio/anaconda3:2020.11

   module load python/3.8-anaconda-2020.11

   ips.py --config=ips.conf --platform=platform.conf


