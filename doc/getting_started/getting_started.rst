===============
Getting Started
===============

This document will guide you through the process of running an IPS simulation and describe the overall structure of the IPS.  It is designed to help you build and run your first IPS simulation.  It will serve as a tutorial on how to get, build, and run your first IPS simulation, but not serve as a general reference for constructing and running IPS simulations.  See the :doc:`Basic User Guides<../user_guides/user_guides>` for a handy reference on running and constructing simulations in general, and for more in-depth explanations of how and why the IPS works.

.. warning::

   The were major changes in IPS from the old (up to July 2020) way of
   doing things to a new way. See :doc:`../user_guides/migration`.

Obtaining, Dependencies, Platforms
==================================

The IPS code is currently located on the GitHub repository. In order to checkout a copy, you must have git installed on the machine you will be using. Once you have git you can check out the IPS thusly::

      git clone https://github.com/HPC-SimTools/IPS-framework.git ips

Dependencies
------------

**IPS Proper**

The IPS framework is written in Python_, and requires Python 3.6+.  There are a few other packages that may be needed for certain components or utilities.  The framework does use the Python package ConfigObj_, however the source is already included and no package installation is necessary (likewise for Python 3.6 and the processing module).

Other Utilities
---------------

**Resource Usage Simulator (RUS)**
  This is a utility for simulation the execution of tasks in the IPS
  for research purposes.

  Requires: Matplotlib_ (which requires Numpy_/Scipy_)

  .. warning::
     The RUS (Resource Usage Simulator) has not been updated to python
     3 or for the changes in IPS and will not function in it current
     state.

**Documentation**
  The documentation you are reading now was created by a Python-based
  tool called Sphinx.

  Requires: Sphinx_


***Plus*** anything that the components or underlying codes that you are using need (e.g., MPI, math libraries, compilers).  For the example in this tutorial, all packages that are needed are already available on the target machines and the shell configuration script sets up your environment to use them.

.. _Sphinx: https://www.sphinx-doc.org
.. _Matplotlib: https://matplotlib.org
.. _Numpy: https://numpy.org
.. _Scipy: https://numpy.org
.. _ConfigObj: http://configobj.readthedocs.io
.. _Python: http://python.org

.. _installing-ips:

Building and Setting up Your Environment
========================================

IPS can be installed directly from github with pip

.. code-block:: bash

  python -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git

otherwise you can download the source code and install from there.

You can install a particular version by, for examples version ``v0.2.0``

.. code-block:: bash

  python -m pip install git+https://github.com/HPC-SimTools/IPS-framework.git@v0.2.0


Installing IPS
--------------

Download IPS from source

.. code-block:: bash

  git clone https://github.com/HPC-SimTools/IPS-framework.git

Install in current python environment, from within the IPS-framework
source directory

.. code-block:: bash

  python -m pip install .
  # or
  python setup.py install

If you are using the system python and don't want to install as root
you can do a user only install with

.. code-block:: bash

  python setup.py install --user

Install in develop mode (this doesn't actually install the package but
creates an egg link)

.. code-block:: bash

  python setup.py develop
  # or
  python -m pip install -e .

``ips.py`` should now be installed in your ``PATH`` and you should be
able to run
``ips.py --config=simulation.config --platform=platform.conf``


.. note::
   You may need to use ``pip3`` and ``python3`` if you default
   ``python`` is not ``python3``.

Create and install in conda environment
---------------------------------------

.. note::

   For specific instruction on setting up conda environments on NERSC
   set :doc:`../user_guides/nersc_conda`.

First you need conda, you can either install the full `Anaconda
package <https://www.anaconda.com/downloads>`_ or `Minconda
<https://docs.conda.io/en/latest/miniconda.html>`_ (recommenced) which
is a minimal installer for conda.

First create a conda environment and activate it, this environment is named
``ips``. You can use any version of python >= 3.6

.. code-block:: bash

  conda create -n ips python=3.9
  conda activate ips

Next install IPS into this environment. From within the IPS-framework
source directory

.. code-block:: bash

  python setup.py install

And you are good to go.

To leave your conda environment

.. code-block:: bash

  conda deactivate

IPS Directory Structure
-----------------------

Before running your first simulation, we should go over the contents of these selected ``ips`` subdirectories.

*ips/*

     *bin/*

         Transient. Installation directory for all executable objects (binaries, scripts) which are generally expected to be invoked by users.  Also expected installation location for executables from external packages which IPS needs to operate.

     *components/*

         *class1/*

         *class2/*

         *...*

             Subversion.  Each class of component wrapper gets its own
             directory tree.  Underneath each class may be multiple
             implementations targeting specific packages.  Various
             component wrappers of a given class will share some source
             code, and require some individual code.

     *doc/*

         Subversion. Documentation. Hierarchy is not specifically designed, but would generally be expected to relate to the various components and packages involved in IPS.

     *framework/*

	  Subversion. Framework source code and utilities reside here. Generally used by framework developers. Relevant Python scripts are placed in ips/bin/ during make install for execution.

----------------------------------

**Explanation and Rationale**


The IPS directory hierarchy is designed to provide a (mostly)
self-contained work space for IPS developers and users.  Multiple
instances of the IPS tree (with different names, of course), can
coexist in the same parent directory without interference.

The caveat "mostly", above, arises from the fact that not all required
packages will be under version control by the SWIM project.  The
expectation is that such packages will be built separately, but
installed into directories within the ips/ tree, and that ips/bin,
ips/lib, etc. will be the only directories users will have to add to
their paths to use their IPS installation.

Subdirectories in the tree are either transient or under Subversion
control.  Transient directories are created and populated as part of
the installation process of either IPS code or external code.  They
should never appear within the Subversion repository.  In fact, the
Subversion repository is configured to ignore directories marked below
as transient.

Running Your First IPS Simulations
==================================

This section will take you step-by-step through running a "hello world" example and a "model physics" example.  These examples contain all of the configuration, batch script, component, executables and input files needed to run them.  To run IPS simulations in general, these will need to be borrowed, modified or created.  See the :doc:`Basic User Guides<../user_guides/user_guides>` for more information.

Before getting started, you will want to make sure you have a copy of the ips checked out and built on either Franklin or Stix.

       On **Franklin** you will want to work in your ``$SCRATCH`` directory and move to having the output from more important runs placed in the ``/project/projectdirs/m876/*`` directory.

       On **Stix** you will want to work in a directory within ``/p/swim1/`` that you own.  You can keep important runs there or in ``/p/swim1/data/``.

Hello World Example
-------------------

This example simply uses the IPS to print "Hello World," using a single driver component and worker component.  The driver component (hello_driver.py) invokes the worker component (hello_worker.py) that then prints a message.  The implementations of these components reside in ``ips/components/drivers/hello/``, if you would like to examine them.  In this example, the *call()* and *launch_task()* interfaces are demonstrated.  In this tutorial, we are focusing on running simulations and will cover the internals of components and constructing simulation scenarios in the various User Guides (see :doc:`Index<../index>`).

1. Copy the following files to your working directory:

   * Configuration file::

     		   /ips/doc/examples/hello_world.config

   * Batch script:: 
     	   	  
		  /ips/doc/examples/<machine>/sample_batchscript.<machine>

2. Edit the configuration file:

   * Set the location of your web-enabled directory for the portal to watch and for you to access your data via the portal.  If you do not have a web-enabled directory, you will have to create one using the following convention: on Franklin: ``/project/projectdirs/m876/www/<username>``; on Stix: ``/p/swim/w3_html/<username>``.

	Franklin::

	    USER_W3_DIR = /project/projectdirs/m876/www/<username>
	    USER_W3_BASEURL = http://portal.nersc.gov/project/m876/<username>

	Stix::

	    USER_W3_DIR = /p/swim/w3_html/<username>
	    USER_W3_BASEURL = http://w2.pppl.gov/swim/<username>

     This step allows the framework to talk to the portal, and for the portal to access the data generated by this run.
   
   * Edit the *IPS_ROOT* to be the absolute path to the IPS checkout that you built.  This tells the framework where the IPS scripts are::

       IPS_ROOT = /path/to/ips


   * Edit the *SIM_ROOT* to be the absolute path to the output tree that will be generated by this simulation.  Within that tree, there will be work directories for each of the components to execute for each time step, along with other logging files.  For this example you will likely want to place the *SIM_ROOT* as the directory where you are launching your simulations from, and name it using the *SIM_NAME*::

       SIM_ROOT = /current/path/${SIM_NAME}

   * Edit the *USER* entry that is used by the portal, identifying you as the owner of the run::

       USER = <username>


3. Edit the batch script such that *IPS_ROOT* is set to the location of your IPS checkout::

     IPS_ROOT=/path/to/ips

4. Launch batch script::

     head_node: ~ > qsub hello_batchscript.<machine>


Once your job is running, you can monitor is on the portal_.

.. image:: swim_portal.png
   :alt: Screen shot of SWIM Portal

When the simulation has finished, the output file should contain::

     Starting IPS
     Created <class 'hello_driver.HelloDriver'>
     Created <class 'hello_worker.HelloWorker'>
     HelloDriver: beginning step call
     Hello from HelloWorker
     HelloDriver: finished worker call

Model Physics Example
---------------------

This simulation is intended to look almost like a real simulation, short of requiring actual physics codes and input data.  Instead typical simulation-like data is generated from simple analytic (physics-less) models for most of the plasma state quantities that are followed by the *monitor* component.  This "model" simulation includes time stepping, time varying scalars and profiles, and checkpoint/restart.  

The following components are used in this simulation:

   * ``minimal_state_init.py`` : simulation initialization for this model case
   * ``generic_driver.py`` : general driver for many different simulations
   * ``model_epa_ps_file_init.py`` : model equilibrium and profile advance component that feeds back data from a file in lieu of computation
   * ``model_RF_IC_2_mcmd.py`` : model ion cyclotron heating
   * ``model_NB_2_mcmd.py`` : model neutral beam heating
   * ``model_FUS_2_mcmd.py`` : model fusion heating and reaction products
   * ``monitor_comp.py`` : real monitor component used by many simulations that helps with processing of data and visualizations that are produced after a run

First, we will run the simulation from time 0 to 20 with checkpointing turned on, and then restart it from a checkpoint taken at time 12.

1. Copy the following files to your working directory:

   * Configuration files::
 
     		   /ips/doc/examples/seq_model_sim.config
		   /ips/doc/examples/restart_12_sec.config

   * Batch scripts::

		   /ips/doc/examples/model_sim_bs.<machine>
     		   /ips/doc/examples/restart_bs.<machine>

2. Edit the configuration files (you will need to do this in BOTH files, unless otherwise noted):

   * Set the location of your web-enabled directory for the portal to watch and for you to access your data via the portal.

	Franklin::

	    USER_W3_DIR = /project/projectdirs/m876/www/<username>
	    USER_W3_BASEURL = http://portal.nersc.gov/project/m876/<username>

	Stix::

	    USER_W3_DIR = /p/swim/w3_html/<username>
	    USER_W3_BASEURL = http://w2.pppl.gov/swim/<username>

     This step allows the framework to talk to the portal, and for the portal to access the data generated by this run.
   
   * Edit the *IPS_ROOT* to be the absolute path to the IPS checkout that you built.  This tells the framework where the IPS scripts are::

       IPS_ROOT = /path/to/ips


   * Edit the *SIM_ROOT* to be the absolute path to the output tree that will be generated by this simulation.  Within that tree, there will be work directories for each of the components to execute for each time step, along with other logging files.  For this example you will likely want to place the *SIM_ROOT* as the directory where you are launching your simulations from, and name it using the *SIM_NAME*::

       SIM_ROOT = /current/path/${SIM_NAME}

   * Edit the *RESTART_ROOT* in ``restart_12_sec.config`` to be the *SIM_ROOT* of ``seq_model_sim.config``. 

   * Edit the *USER* entry that is used by the portal, identifying you as the owner of the run::

       USER = <username>


3. Edit the batch script such that *IPS_ROOT* is set to the location of your IPS checkout::

     IPS_ROOT=/path/to/ips

4. Launch batch script for the original simulation::

     head_node: ~ > qsub model_sim_bs.<machine>


Once your job is running, you can monitor is on the portal_ and it should look like this:

.. image:: swim_portal_orig.png
   :alt: Screenshot of model run

When the simulation has finished, you can run the restart version to restart the simulation from time 12::

     head_node: ~ > qsub restart_bs.<machine>

The job on the portal should look like this when it is done:

.. image:: swim_portal_restart.png
   :alt: Screenshot of restart run


.. _Franklin: http://www.nersc.gov/users/computational-systems/franklin/
.. _portal: http://swim.gat.com:8080/display/
