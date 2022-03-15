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

.. _dask_shifter:

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


Running with worker plugin
--------------------------

There is the ability to set a
:class:`~distributed.diagnostics.plugin.WorkerPlugin` on the dask
worker using the `dask_worker_plugin` option in
:meth:`~ipsframework.services.ServicesProxy.submit_tasks`.

Using a WorkerPlugin in combination with shifter allows you to do
things like coping files out of the `Temporary XFS
<https://docs.nersc.gov/development/shifter/how-to-use/#temporary-xfs-files-for-optimizing-io>`_
file system. An example of that is

.. code-block:: python

    from distributed.diagnostics.plugin import WorkerPlugin

    class CopyWorkerPlugin(WorkerPlugin):
        def __init__(self, tmp_dir, target_dir):
            self.tmp_dir = tmp_dir
            self.target_dir = target_dir

        def teardown(self, worker):
            os.system(f"cp {self.tmp_dir}/* {self.target_dir}")

    class Worker(Component):
        def step(self, timestamp=0.0):
            cwd = self.services.get_working_dir()
            tmp_xfs_dir = '/tmp'

            self.services.create_task_pool('pool')
            self.services.add_task('pool', 'task_1', 1, tmp_xfs_dir, 'executable')

            worker_plugin = CopyWorkerPlugin(tmp_xfs_dir, cwd)

            ret_val = self.services.submit_tasks('pool',
                                                 use_dask=True, use_shifter=True,
                                                 dask_worker_plugin=worker_plugin)

            exit_status = self.services.get_finished_tasks('pool')


where the batch script has the temporary XFS filesystem mounted as

.. code-block:: bash

    #SBATCH --volume="/global/cscratch1/sd/$USER/tmpfiles:/tmp:perNodeCache=size=1G"


Continuous Archiving
^^^^^^^^^^^^^^^^^^^^

Another example is a WorkerPlugin that will continuously create a tar
archive of the output data at a regular interval while tasks are
executing. This is useful should the workflow fail or is canceled
before everything is finished. It creates a separate achieve for each
node/worker since the temporary XFS filesystem is unique per
node. This example creates an archive of all the data in the working
directory every 60 seconds and again when everything is finished.

.. code-block:: python

    def file_daemon(worker_id, evt, source_dir, target_dir):
        cmd = f"tar -caf {target_dir}/{worker_id}_archive.tar.gz -C {source_dir} ."

        while not evt.wait(60):  # interval which to archive data
            os.system(cmd)

        os.system(cmd)

    class ContinuousArchivingWorkerPlugin(WorkerPlugin):
        def __init__(self, tmp_dir, target_dir):
            self.tmp_dir = tmp_dir
            self.target_dir = target_dir

        def setup(self, worker):
            self.evt = Event()
            self.thread = Thread(target=file_daemon, args=(worker.id, self.evt, self.tmp_dir, self.target_dir))
            self.thread.start()

        def teardown(self, worker):
            self.evt.set()  # tells the thread to exit
            self.thread.join()

    class Worker(Component):
        def step(self, timestamp=0.0):
            cwd = self.services.get_working_dir()
            tmp_xfs_dir = '/tmp'

            self.services.create_task_pool('pool')
            self.services.add_task('pool', 'task_1', 1, tmp_xfs_dir, 'executable')

            worker_plugin = ContinuousArchivingWorkerPlugin(tmp_xfs_dir, cwd)

            ret_val = self.services.submit_tasks('pool',
                                                 use_dask=True, use_shifter=True,
                                                 dask_worker_plugin=worker_plugin)

            exit_status = self.services.get_finished_tasks('pool')


where the batch script has the temporary XFS filesystem mounted as

.. code-block:: bash

    #SBATCH --volume="/global/cscratch1/sd/$USER/tmpfiles:/tmp:perNodeCache=size=1G"
