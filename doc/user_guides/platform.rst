====================================
Platforms and Platform Configuration
====================================

This section will describe key aspects of the platforms that the IPS has been ported to, key locations relevant to the IPS, and the platform configuration settings in general and specific to the platforms described below.

**Important Note** - while this documentation is intended to remain up to date, it may not always reflect the current status of the machines.  If you run into problems, check that the information below is accurate by looking at the websites for the machine.  If you are still having problems, contact the framework developers.

----------------
Ported Platforms
----------------

Each subsection will contain information about the platform in question.  If you are porting the IPS to a new platform, these are the items that you will need to know or files and directories to create in order to port the IPS.  You will also need a platform configuration file (:ref:`described below<plat-conf-sec>`).  Available queue names are listed with the most common ones in **bold**.

The platforms below fall into the following categories: 

  * general production machines - large production machines on which the majority of runs (particularly production runs) are made.  
  * experimental systems - production or shared machines that are being used by a subset of SWIM members for specific research projects.  These systems may also be difficult for others to get accounts.
  * formerly used systems - machines that the IPS was ported to but we either do not have time on that machine, it has been retired by its hosting site, or it is not in wide use anymore.
  * single user systems - laptop or desktop machines for testing small problems.

^^^^^^^^^^^^^^^^^^
General Production
^^^^^^^^^^^^^^^^^^
:::::::::
Cori
:::::::::

Cori_ is a Cray XC40 managed by NERSC_.

* Account: You must have an account at NERSC and be added to the Atom project's group (atom) to log on and access the set of physics binaries in the *PHYS_BIN*.
* Logging on - ``ssh cori.nersc.gov -l <username>``
* Architecture - 2,388 Haswell nodes, 32 cores per node, 128GB memory per node + 9,668 KNL nodes, 68 cores per node, 96 GB memory
* Environment:

  * OS - SUSE Linux Enterprise Server 15 (SLES15)
  * Batch scheduler/Resource Manager - Slurm
  * `Queues <https://docs.nersc.gov/jobs/policy/>`__ - **debug**, **regular**, premium, interactive, ...
  * Parallel Launcher (e.g., mpirun) - srun
  * Node Allocation policy - exclusive or shared node allocation

* Project directory - ``/global/project/projectdirs/atom``
* Data Tree - ``/global/common/software/atom/cori/data``
* Physics Binaries - ``/global/common/software/atom/cori/binaries``
* WWW Root - ``/global/project/projectdirs/atom/www/<username>``
* WWW Base URL - ``http://portal.nersc.gov/project/atom/<username>``

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Retired/Formerly Used Systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:::::::::
Franklin
:::::::::

Franklin_ is a Cray XT4 managed by NERSC_.  

* Account: You must have an account at NERSC and be added to the SWIM project's group (m876) to log on and access the set of physics binaries in the *PHYS_BIN*.
* Logging on - ``ssh franklin.nersc.gov -l <username>``
* Architecture - 9,572 nodes, 4 cores per node, 8 GB memory per node
* Environment:

  * OS - Cray Linux Environment (CLE)
  * Batch scheduler/Resource Manager - PBS, Moab
  * `Queues <http://www.nersc.gov/users/computational-systems/franklin/running-jobs/queues-and-policies/>`__ - **debug**, **regular**, low, premium, interactive, xfer, iotask, special
  * Parallel Launcher (e.g., mpirun) - aprun
  * Node Allocation policy - exclusive node allocation

* Project directory - ``/project/projectdirs/m876/``
* Data Tree - ``/project/projectdirs/m876/data/``
* Physics Binaries - ``/project/projectdirs/m876/phys-bin/phys/``
* WWW Root - ``/project/projectdirs/m876/www/<username>``
* WWW Base URL - ``http://portal.nersc.gov/project/m876/<username>``

:::::::::
Hopper
:::::::::

Hopper_ is a Cray XE6 managed by NERSC_.  

* Account: You must have an account at NERSC and be added to the SWIM project's group (m876) to log on and access the set of physics binaries in the *PHYS_BIN*.
* Logging on - ``ssh hopper.nersc.gov -l <username>``
* Architecture - 6384 nodes, 24 cores per node, 32 GB memory per node
* Environment:

  * OS - Cray Linux Environment (CLE)
  * Batch scheduler/Resource Manager - PBS, Moab
  * `Queues <http://www.nersc.gov/users/computational-systems/hopper/running-jobs/queues-and-policies/>`__ - **debug**, **regular**, low, premium, interactive
  * Parallel Launcher (e.g., mpirun) - aprun
  * Node Allocation policy - exclusive node allocation

* Project directory - ``/project/projectdirs/m876/``
* Data Tree - ``/project/projectdirs/m876/data/``
* Physics Binaries - ``/project/projectdirs/m876/phys-bin/phys/``
* WWW Root - ``/project/projectdirs/m876/www/<username>``
* WWW Base URL - ``http://portal.nersc.gov/project/m876/<username>``

:::::::::
Stix
:::::::::

Stix_ is a SMP hosted at PPPL_.

* Account: You must have an account at PPPL to access their Beowulf systems.
* Logging on:

  1. Log on to the PPPL vpn (https://vpn.pppl.gov)
  2. ``ssh <username>@portal.pppl.gov``
  3. ``ssh portalr5``

* Architecture - 80 cores, 440 GB memory
* Environment:

  * OS - linux
  * Batch scheduler/Resource Manager - PBS (Torque), Moab
  * `Queues <http://beowulf.pppl.gov/queues.html>`__ - **smpq** (this is how you specify that you want to run your job on stix)
  * Parallel Launcher (e.g., mpirun) - mpiexec (MPICH2)
  * Node Allocation policy - node sharing allowed (whole machine looks like one node)

* Project directory - ``/p/swim1/``
* Data Tree - ``/p/swim1/data/``
* Physics Binaries - ``/p/swim1/phys/``
* WWW Root - ``/p/swim/w3_html/<username>``
* WWW Base URL - ``http://w3.pppl.gov/swim/<username>``

:::::::::
Viz/Mhd
:::::::::

`Viz/mhd`_ are SMP machines hosted at PPPL_.  These systems appear not to be online any more.

.. note : Retired?

* Account: You must have an account at PPPL to access their Beowulf systems.
* Logging on:

  1. Log on to the PPPL vpn (https://vpn.pppl.gov)
  2. ``ssh <username>@portal.pppl.gov``

* Architecture - ? cores, ? GB memory
* Environment:

  * OS - linux
  * Batch scheduler/Resource Manager - PBS (Torque), Moab
  * Parallel Launcher (e.g., mpirun) - mpiexec (MPICH2)
  * Node Allocation policy - node sharing allowed (whole machine looks like one node)

* Project directory - ``/p/swim1/``
* Data Tree - ``/p/swim1/data/``
* Physics Binaries - ``/p/swim1/phys/``
* WWW Root - ``/p/swim/w3_html/<username>``
* WWW Base URL - ``http://w3.pppl.gov/swim/<username>``

:::::::::::
Pingo
:::::::::::

Pingo_ was a Cray XT5 hosted at ARSC_.

.. note : Retired machine.

.. note : I do not have information about this machine.  Someone who has access needs to update this entry and modify the configuration file with the new entries (see below).

* Account: You must have an account to log on and use the system.
* Logging on - ?
* Architecture - 432 nodes, 8 cores per node, ? memory per node
* Environment:

  * OS - ?
  * Batch scheduler/Resource Manager - ?
  * Parallel Launcher (e.g., mpirun) - aprun
  * Node Allocation policy - exclusive node allocation

* Project directory - ?
* Data Tree - ?
* Physics Binaries - ?
* WWW Root - ?
* WWW Base URL - ?

:::::::::::
Jaguar
:::::::::::

Jaguar_ is a Cray XT5 managed by OLCF_.

.. note : Previously had time on this machine, but do not at this time.

* Account: You must have an account for the OLCF and be added to the SWIM project group for accounting and files sharing purposes, if we have time on this machine.
* Logging on - ``ssh jaguar.ornl.gov -l <username>``
* Architecture - 13,688 nodes, 12 cores per node, 16 GB memory per node
* Environment:

  * OS - Cray Linux Environment (CLE)
  * Batch scheduler/Resource Manager - PBS, Moab
  * `Queues <http://www.nccs.gov/computing-resources/jaguar/running-jobs/scheduling-policy-xt5/>`__ - debug, production
  * Parallel Launcher (e.g., mpirun) - aprun
  * Node Allocation policy - exclusive node allocation

* Project directory - ?
* Data Tree - ?
* Physics Binaries - ?
* WWW Root - ?
* WWW Base URL - ?

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Experimental Systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:::::::::
Swim
:::::::::

Swim_ is a SMP hosted by the `fusion theory group`_ at ORNL.

* Account: You must have an account at ORNL and be given an account on the machine.
* Logging on - ``ssh swim.ornl.gov -l <username>``
* Architecture - ? cores, ? GB memory
* Environment:

  * OS - linux
  * Batch scheduler/Resource Manager - None
  * Parallel Launcher (e.g., mpirun) - mpirun (OpenMPI)
  * Node Allocation policy - node sharing allowed (whole machine looks like one node)

* Project directory - None
* Data Tree - None
* Physics Binaries - None
* WWW Root - None
* WWW Base URL - None

:::::::::
Pacman
:::::::::

Pacman_ is a linux cluster hosted at ARSC_.

.. note : I do not have information about this machine.  Someone who has access needs to update this entry and modify the configuration file with the new entries (see below).

* Account: You must have an account to log on and use the system.
* Logging on - ?
* Architecture:

  * 88 nodes, 16 cores per node, 64 GB per node
  * 44 nodes, 12 cores per node, 32 GB per node

* Environment:

  * OS - Red Hat Linux 5.6
  * Batch scheduler/Resource Manager - Torque (PBS), Moab
  * `Queues <http://www.arsc.edu/support/news/systemnews/news.xml?system=pacman#1294294578>`__ - debug, standard, standard_12, standard_16, bigmem, gpu, background, shared, transfer
  * Parallel Launcher (e.g., mpirun) - mpirun (OpenMPI?)
  * Node Allocation policy - node sharing allowed

* Project directory - ?
* Data Tree - ?
* Physics Binaries - ?
* WWW Root - ?
* WWW Base URL - ?

:::::::::
Iter
:::::::::

Iter_ is a linux cluster (?) that is hosted ???.

.. note : I do not have information about this machine.  Someone who has access needs to update this entry and modify the configuration file with the new entries (see below).

* Account: You must have an account to log on and use the system.
* Logging on - ?
* Architecture - ? nodes, ? cores per node, ? GB memory per node
* Environment:

  * OS - linux
  * Batch scheduler/Resource Manager - ?
  * Queues - ?
  * Parallel Launcher (e.g., mpirun) - mpiexec (MPICH2)
  * Node Allocation policy - node sharing allowed

* Project directory - ``/project/projectdirs/m876/``
* Data Tree - ``/project/projectdirs/m876/data/``
* Physics Binaries - ``/project/projectdirs/m876/phys-bin/phys/``
* WWW Root - ?
* WWW Base URL - ?


:::::::::
Odin
:::::::::

Odin_ is a linux cluster hosted at `Indiana University`_.

* Account: You must have an account to log on and use the system.
* Logging on - ``ssh odin.cs.indiana.edu -l <username>``
* Architecture - 128 nodes, 4 cores per node, ? GB memory per node
* Environment:

  * OS - GNU/Linux
  * Batch scheduler/Resource Manager - Slurm, Maui
  * Queues - there is only one queue and it does not need to specified in the batchscript
  * Parallel Launcher (e.g., mpirun) - mpirun (OpenMPI)
  * Node Allocation policy - node sharing allowed

* Project directory - None
* Data Tree - None
* Physics Binaries - None
* WWW Root - None
* WWW Base URL - None

:::::::::
Sif
:::::::::

Sif_ is a linux cluster hosted at `Indiana University`_.

* Account: You must have an account to log on and use the system.
* Logging on - ``ssh sif.cs.indiana.edu -l <username>``
* Architecture - 8 nodes, 8 cores per node, ? GB memory per node
* Environment:

  * OS - GNU/Linux
  * Batch scheduler/Resource Manager - Slurm, Maui
  * Queues - there is only one queue and it does not need to specified in the batchscript
  * Parallel Launcher (e.g., mpirun) - mpirun (OpenMPI)
  * Node Allocation policy - node sharing allowed

* Project directory - None
* Data Tree - None
* Physics Binaries - None
* WWW Root - None
* WWW Base URL - None

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Single User Systems
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The IPS can be run on your laptop or desktop.  Many of the items above are not present or relevant in a laptop/desktop environment.  See the next section for a sample platform configuration settings.



.. _Cori: https://docs.nersc.gov/systems/cori/
.. _Hopper: http://www.nersc.gov/nusers/systems/hopper/
.. _Franklin: http://www.nersc.gov/nusers/systems/franklin/
.. _Pacman: http://www.arsc.edu/resources/pacman.html
.. _Pingo: http://www.arsc.edu/support/news/systemnews/news.xml?system=pingo
.. _Viz/mhd: http://beowulf.pppl.gov/
.. _Stix: http://beowulf.pppl.gov/
.. _ARSC: http://www.arsc.edu/
.. _Sif: https://uisapp2.iu.edu/confluence-prd/pages/viewpage.action?pageId=131203559
.. _Odin: https://uisapp2.iu.edu/confluence-prd/pages/viewpage.action?pageId=131203559
.. _Indiana University: http://www.soic.indiana.edu/
.. _NERSC: http://www.nersc.gov/
.. _PPPL: http://www.pppl.gov/
.. _fusion theory group: http://www.ornl.gov/sci/fed/Theory/
.. _OLCF: http://www.olcf.ornl.gov/
.. _Jaguar: http://www.olcf.ornl.gov/computing-resources/jaguar/

.. _plat-conf-sec:

---------------------------
Platform Configuration File
---------------------------
The platform configuration file contains platform specific information that the framework needs.  Typically it does not need to be changed for one user to another or one run to another (except for manual specification of allocation resources).  For *most* of the platforms above, you will find platform configuration files of the form ``<machine name>.conf``.  It is not likely that you will need to change this file, but it is described here for users working on experimental machines, manual specification of resources, and users who need to port the IPS to a new machine.

::

  HOST = cori
  MPIRUN = srun

  #######################################
  # resource detection method
  #######################################

  NODE_DETECTION = slurm_env # checkjob | qstat | pbs_env | slurm_env

  #######################################
  # node topology description
  #######################################

  PROCS_PER_NODE = 32
  CORES_PER_NODE = 32
  SOCKETS_PER_NODE = 1

  #######################################
  # framework setting for node allocation
  #######################################
  # MUST ADHERE TO THE PLATFORM'S CAPABILITIES
  #   * EXCLUSIVE : only one task per node
  #   * SHARED : multiple tasks may share a node
  # For single node jobs, this can be overridden allowing multiple
  # tasks per node.

  NODE_ALLOCATION_MODE = EXCLUSIVE # SHARED | EXCLUSIVE
  USE_ACCURATE_NODES = ON

**HOST**
        name of the platform.  Used by the portal.
**MPIRUN**
        command to launch parallel applications.  Used by the task
	manager to launch parallel tasks on compute nodes.  If you
	would like to launch a task directly without the parallel
	launcher (say, on a SMP style machine or workstation), set
	this to "eval" -- it tells the task manager to directly launch 	the task as ``<binary> <args>``.
**NODE_DETECTION**
        method to use to detect the number of nodes and processes in
	the allocation.  If the value is "manual," then the manual
	allocation description is used.  If nothing is specified, all
	of the methods are attempted and the first one to succeed will
	be used.  Note, if the allocation detection fails, the
	framework will abort, killing the job.
**TOTAL_PROCS**
        number of processes in the allocation [#manual_alloc_node]_.
**NODES**
        number of nodes in the allocation [#manual_alloc_node]_.
**PROCS_PER_NODE**
        number of processes per node (ppn) for the framework 
	[#manual_alloc_ppn]_.
**CORES_PER_NODE**
        number of cores per node [#nochange]_.
**SOCKETS_PER_NODE**
        number of sockets per node [#nochange]_.
**NODE_ALLOCATION_MODE**
        'EXCLUSIVE' for one task per node, and 'SHARED' if more than
	one task can share a node [#nochange]_.  Simulations,
	components and tasks can set their node usage allocation
	policies in the configuration file and on task launch.


.. [#nochange] This value should not change unless the machine is
   upgraded to a different architecture or implements different
   allocation policies.

.. [#manual_alloc_ppn]  Used in manual allocation detection and will
   override any detected ppn value (if smaller than the machine
   maximum ppn).

.. [#manual_alloc_node] Only used if manual allocation is specified,
   or if no detection mechanism is specified and none of the other
   mechansims work first.  It is the *users* responsibility for this
   value to make sense.


.. note : the node allocation and detection values in this file can be overriden by command line options to the ips ``--nodes`` and ``--ppn``.  *Both* values must be specified, otherwise the platform configuration values are used.

A sample platform configuration file for a workstation.  It assumes that the workstation:

  * does not have a batch scheduler or resource manager
  * may have multiple cores and sockets
  * does not have portal access
  * will manually specify the allocation

::

  HOST = workstation
  MPIRUN = mpirun # eval

  #######################################
  # resource detection method
  #######################################
  NODE_DETECTION = manual # checkjob | qstat | pbs_env | slurm_env | manual

  #######################################
  # manual allocation description
  #######################################
  TOTAL_PROCS = 4
  NODES = 1
  PROCS_PER_NODE = 4

  #######################################
  # node topology description
  #######################################
  CORES_PER_NODE = 4
  SOCKETS_PER_NODE = 1

  #######################################
  # framework setting for node allocation
  #######################################
  # MUST ADHERE TO THE PLATFORM'S CAPABILITIES
  #   * EXCLUSIVE : only one task per node
  #   * SHARED : multiple tasks may share a node
  # For single node jobs, this can be overridden allowing multiple
  # tasks per node.
  NODE_ALLOCATION_MODE = SHARED # SHARED | EXCLUSIVE


.. [#manual_only] These need to be updated to match the "allocation"
   size each time.  Alternatively, you can just use the 
   :doc:`command line<basic_guide>` to specify the number of nodes 
   and processes per node.
