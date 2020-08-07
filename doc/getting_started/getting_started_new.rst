Getting Started with the Simyan Branch
======================================

This document will guide you through the process of running an IPS
simulation and describe the overall structure of the IPS.  It is
designed to help you build and run your first IPS simulation.  It will
serve as a tutorial on how to get, build, and run your first IPS
simulation, but not serve as a general reference for constructing and
running IPS simulations.  See the :doc:`Basic User
Guides<../user_guides/user_guides>` for a handy reference on running and
constructing simulations in general, and for more in-depth explanations
of how and why the IPS works.

^^^^^^^^^^^^^^^^^^^
Dependencies
^^^^^^^^^^^^^^^^^^^

**IPS Proper**

The valtools repo will build the entire dependency tree for IPS,
related repos, and the dependencies using Bilder_.   See the main
documentation for the dependencies.

For more inf

**Portal**

The portal is a web interface for monitoring IPS runs and requires only
a connection to the internet and a web browser.  Advanced features on
the portal require an OpenID account backed by ORNL's XCAMS.
Information on getting an XCAMS backed OpenID can be found on the _SWIM
website.  There are also visualization utilities that can be accessed
that require Elvis_ or PCMF (see below).

::::::::::::::::
Other Utilities
::::::::::::::::

**PCMF**
  This utility generates plots from monitor component files for visual analysis of runs.  It can be run locally on your machine and generates plots like this one of the thermal profiles of an ITER run:

  Requires: Matplotlib_ (which requires `Numpy/Scipy`_)


  .. image:: thermal_profiles.png
      :alt: thermal profiles of an ITER run

**Resource Usage Simulator (RUS)**
  This is a utility for simulation the execution of tasks in the IPS
  for research purposes.

  Requires: Matplotlib_ (which requires `Numpy/Scipy`_)

**Documentation**
  The documentation you are reading now was created by a Python-based
  tool called Sphinx.

  Requires: Sphinx_ (which requires docutils_)


***Plus*** anything that the components or underlying codes that you are using need (e.g., MPI, math libraries, compilers).  For the example in this tutorial, all packages that are needed are already available on the target machines and the shell configuration script sets up your environment to use them.

.. _Sphinx: http://sphinx.pocoo.org/
.. _Matplotlib: http://matplotlib.sourceforge.net/
.. _Numpy/Scipy: http://numpy.scipy.org/
.. _Elvis: http://w3.pppl.gov/elvis/
.. _docutils: http://docutils.sourceforge.net/
.. _ConfigObj: http://www.voidspace.org.uk/python/configobj.html
.. _Python: http://python.org/
.. _processing: http://pypi.python.org/pypi/processing
.. _multiprocessing: http://docs.python.org/library/multiprocessing.html
.. _Bilder: https://ice.txcorp.com/trac/bilder

=====================================================
Building and Setting up Your Environment Using Bilder
=====================================================
  
The IPS code is currently located in the SWIM project's Subversion (SVN)
repository.  In this documentation, we will discuss using it from the
Tech-X repos to discuss the new repos.  IPS is currently part of the
Simyan repo which is svn:external'd from the ValtoolsAll repo.  The
valtoolsall repo is for enabling a simplified environment for python
packages.  To check out the valtoolsall repo::

      svn co https://ice.txcorp.com/svnrepos/code/valtoolsall/trunk valtoolsall

Using bilder and the valtoolsall project::

  cd valtoolsall
  ./mkvaltoolsall-default.sh -n

After running bilder, the output file will tell you where things are
installed (<INSTALL_DIR>) and where things are built (<BUILD_DIR>).  To
configure your environment, you need to source the configuration files.
For bash users::

   source <INSTALL_DIR>/valtoolsall.sh

For tcsh users::

   source <INSTALL_DIR>/valtoolsall.csh

To test the builds::

  cd <BUILD_DIR>/simyan/ser
  make test

This will run all of the tests.  The documentation, assuming the `-D`
flag was passed to bilder, will be in the webdocs build directory
(`<BUILD_DIR>/simyan/webdocs`).


===========================================================
Building and Setting up Your Environment direct from repo
===========================================================

Assuming you have the dependencies installed, you can jst check out the
repo and configure directly.  To obtain the rep::

      https://ice.txcorp.com/svnrepos/code/simyan/trunk ips

#. Assuming your dependencies are installed in /usr/local or /contrib,
   you can configure the file in a build subdirectory

::

  mkdir build
  cd build
  cmake \
    -DCMAKE_INSTALL_PREFIX:PATH=$INSTALL_DIR/simyan \
    -DCMAKE_BUILD_TYPE:STRING=RELEASE \
    -DCMAKE_VERBOSE_MAKEFILE:BOOL=TRUE \
    -DCMAKE_INSTALL_ALWAYS:BOOL=TRUE \
    -DSUPRA_SEARCH_PATH='/usr/local;/contrb' \
    -DENABLE_WEBDOCS:BOOL=ON \
    -DMPIRUN:STRING=aprun \
    -DNODE_DETECTION:STRING=manual \
    -DCORES_PER_NODE:INTEGER=4 \
    -DSOCKETS_PER_NODE:INTEGER=2 \
    -DNODE_ALLOCATION_MODE:SHARED=shared \
    $PWD/..

# After configuring, to build IPS, the documentation, and run the tests
respectively

::

  make
  make docs
  make test
  make install

The documentation may be found at docs/html/index.html.  The
tests are located in the tests subdirectory.

Now you are ready to set up your configuration files, and run simulations.


===================================
Running Your First IPS Simulations
===================================

This section will take you step-by-step through running a "hello world" example
and a "model physics" example.  These examples contain all of the
configuration, batch script, component, executables and input files needed to
run them.  To run IPS simulations in general, these will need to be borrowed,
modified or created.  See the :doc:`Basic User
Guides<../user_guides/user_guides>` for more information.

Before getting started, you will want to make sure you have a copy of the ips checked out and built on either Franklin or Stix.

       On **Franklin** you will want to work in your ``$SCRATCH`` directory and move to having the output from more important runs placed in the ``/project/projectdirs/m876/*`` directory.

       On **Stix** you will want to work in a directory within ``/p/swim1/`` that you own.  You can keep important runs there or in ``/p/swim1/data/``.

^^^^^^^^^^^^^^^^^^^^
Hello World Example
^^^^^^^^^^^^^^^^^^^^

This example simply uses the IPS to print "Hello World," using a single driver
component and worker component.  The driver component (hello_driver.py) invokes
the worker component (hello_worker.py) that then prints a message.  The
implementations of these components reside in
``ips/components/drivers/hello/``, if you would like to examine them.  In this
example, the *call()* and *launch_task()* interfaces are demonstrated.  In this
tutorial, we are focusing on running simulations and will cover the internals
of components and constructing simulation scenarios in the various User Guides
(see :doc:`Index<../index>`).

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

^^^^^^^^^^^^^^^^^^^^^^
Model Physics Example
^^^^^^^^^^^^^^^^^^^^^^

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
