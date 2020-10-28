Reference Guide for Running IPS Simulations
===========================================

This reference guide is designed to help you through the process of setting up a simulation to run.  It provides instructions on how to change configuration files and how to build and run the IPS on a given platform, as well as, determine if the simulation is setup correctly and will produce the correct data.  In the various sections the user will find a series of questions designed to help the user plan for the preparation, execution, and post-processing of a run (or series of runs).

------------
Terminology
------------

Before going further, some basic definitions of terms that are used in the IPS must be presented.  These terms are specific to the IPS and may be used in other contexts with different meanings.  These are brief definitions and designed to remind the user of their meaning.

-------------------------
Elements of a Simulation
-------------------------

**Head node**
  The *head node* is how this documentation refers to any login, service or head node that acts as the gateway to a cluster or MPP.  It is where the Python codes and some helper scripts run, including the framework, services and components.

**Compute node**
  A *compute node* is a node that exists in the compute partition of a parallel machine.  It is designed for running compute intensive and parallel applications.

**Batch allocation**
  The *batch allocation* is the set of (compute) nodes given to the framework by the system's scheduler.  The framework services manage the allocation of resources and launching of tasks on compute nodes within this allocation.

**Framework**
  The *framework* serves as the structure that contains the components, drivers and services for the simulation(s).  It provides the infrastructure for the different elements to interact.  It is the piece of software that is executed, and uses the services to invoke, run and manage the drivers, components, and tasks.

**Component**
  A *component* is a Python class that interacts with other components (typically the driver) and tasks using the services.  A *physics* component typically uses the Python class to adapt a standalone physics code to be coupled with other components.  Logically, each component contributes something to the simulation at hand, whether it is a framework functionality, like a bridge to the portal, or a model of some physical phenomena, like RF heating sources.

**Task**
  A *task* is an executable that runs on compute node(s) launched by the services on behalf of the component.  These executables are the ones who do the heavy physics computation and dominate the run time, allowing the Python components and framework to manage the orchestration and other services involved in managing a multiphysics simulation.  Most often tasks are parallel codes using MPI for interprocess communication.

**Driver (Component)**
  The *driver* is a special component in that it is the first one to be executed for the simulation.  It is responsible for invoking its constituent components, implementing the time stepping and other logic among components, and global data operations, such as checkpointing.

**Init (Component)**
  The *init* component is a special in that it is invoked by the framework and is the first one to be executed for the simulation.  It is responsible for performing any initialization needed by the driver before it begins its execution cycle.

**Port**
  A *port* is a category of component that can be implemented by different component implementations, i.e., components that wrap codes that different mathematical models of the same phenomenon.  Each component that has the same port must implement the same interface (i.e., implement functions with the same names - in the IPS all components implement "init", "step", and "finalize"), and provide the same functionality in a coupled simulation.  In most cases, this means that it updates the same values in the plasma state.  Drivers use the port name of a component to obtain a reference for that component at run time, as specified in the configuration file.

**Services**
  The framework *services* provide APIs for setting up the simulation, and managing data, resources, tasks, component invocations, access to configuration data and communication via an event service during execution.  For more details, see :doc:`code listings <../the_code>`.  Component writers should check out the :ref:`services API <api_section>` for relevant services and tips on how to use them.

**Data files**
  Each component specifies the input and output *data files* it needs for a given simulation.  These file names and locations are used to stage data in and out for each time step.  Note that these are not the same as the *plasma state files*, in that *data files* are component local (and thus private).

**Plasma State files**
  The *plasma state* is a utility and set of files that allow multiple components to contribute values to a set of files representing the shared data about the plasma.  These shared files are specified in the configuration file and access is managed through the framework services data management API.  Component writers may need to write scripts to translate between plasma state files and the files expected/generated by the underlying executable.

**Configuration file**
  The *configuration file* allows the user to describe how a simulation is to be run.  It uses a third-party Python package called ConfigObj_ to easily parse the shell-like, hierarchical syntax.  In the configuration file there are sections describing the following aspects of the simulation.  They are all explained in further detail in :doc:`The Configuration File - Explained <config_file>`.

**Platform Configuration file**
  The *platform configuration file* contains platform specific information needed by the framework for task and resource management, as well as paths needed by the portal and configuration manager.  These rarely change, so the version in the top level of the IPS corresponding to the platform you are running on should be used.

**Batch script**
  The *batch script* tells the batch scheduler how and what to run, including the number of processes and nodes for the allocation, the command to launch the IPS, and any other information that the batch scheduler needs to know to run your job.

.. _ConfigObj: http://www.voidspace.org.uk/python/configobj.html

----------------
Sample workflow
----------------

This section consists of an outline of how the IPS is intended to be used.  It will walk you through the steps from forming an idea of what to run, through running it and analyzing the results.  This will also serve as a reference for running IPS simulations.  If you are not comfortable with the elements of an IPS simulation, then you should start with the sample simulations in :doc:`Getting Started <../getting_started/getting_started>` and review the terminology above.

:::::::::::::::::
Problem Formation
:::::::::::::::::

Before embarking on a simulation experiment, the problem that you are addressing needs to be determined.  The problem may be a computational one where you are trying to determine if a component works properly, or an experiment to determine the scalability or sensitivity to computation parameters, such as time step length or number of particles.  The problem may pertain to a study of how a component, or set of components, compare to previous results or real data.  The problem may be to figure out for a set of variations which one produces the most stable plasma conditions.  In each case, you will need to determine:

  * what components are needed to perform this experiment?
  * what input files must be obtained, prepared or generated (for each component and the simulation as a whole)?
  * does this set of components make sense?
  * what driver(s) are needed to perform this experiment?
  * do new components and drivers need to be created?
  * does it make sense to run multiple simulations in a single IPS instance?
  * how will multiple simulations effect the computational needs and amount of data that is produced?
  * what plasma state files are needed?
  * where will initial plasma state values (and those not modeled by components in this scenario) come from?
  * how much compute time and resources are needed for each task? the simulation as a whole?
  * are there any restrictions on where or when this experiment can be run?
  * how will the output data be analyzed?
  * where will the output data go when the simulation is completed?
  * when and where will the output data be analyzed?

Once you have a plan for constructing, managing and analyzing the results of your simulation(s), it is time to begin preparation.

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::
A Brief Introduction to Writing and Modifying Components
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::

In many cases, new components or modifications to existing components need to be made.  In this section, the anatomy of a component and a driver are explained for a simple invocation style of execution. (see :doc:`Advanced User Guide <advanced_guide>` for more information on creating components and drivers with complex logic, parallelism and asynchronous control flow).

Each component is derived from the ``Component`` class, meaning that each IPS component inherits a few base capabilities, and then must augment them.  Each IPS component must implement the following function bodies for the component class:

``init(self, timeStamp=0)``
  This function performs pre-simulation setup activities such as reading in global configuration parameters, checking configuration parameters, updating input files and internal state.  (Component configuration parameters are populated *before* ``init`` is ever called.)

``step(self, timeStamp=0)``
  This function is the main part of the component.  It is responsible for launching any tasks, and managing the input, output and plasma state during the course of the step.

``finalize(self, timeStamp=0)``
  This function is called after the simulation has completed and performs any clean up that is required by the component.  Typically there is nothing to do.

``checkpoint(self, timeStamp=0)``
  This function performs a checkpoint for the component.  All of the files marked as restart files in the configuration file are automatically staged to the checkpoint area.  If the component has any internal knowledge or logic, or if there are any additional files that are needed to restart, this should be done explicitly here.

``restart(self, timeStamp=0)``
  This function replaces ``init`` when restarting a simulation from a previous simulation step.  It should read in data from the appropriate files and set up the component so that it is ready to compute the next step.

To create a new component, there are two ways to do it, start from "scratch" by copying and renaming the skeleton component (:download:`skeleton_comp.py <../examples/skeleton_comp.py>`) to your desired location [#]_, or by modifying an existing component (e.g., :download:`example_comp.py <../examples/example_comp.py>`).  When creating your new component, keep in mind that it should be somewhat general and usable in multiple contexts.  In general, for things that change often, you will want to use component configuration variables or input files to drive the logic or set parameters for the tasks.  For more in depth information about how to create components and add them to the build process, see :doc:`Developing Drivers and Components for IPS Simulations <advanced_guide>`.

When changing an existing component that will diverge from the existing version, be sure to create a new version.  If you are editing an existing component to make it better, be sure to document what you changexs.

.. [#] Components are located in the ``ips/components/`` directory and are organized by *port name*, followed by implementation name.  It is also common to put input files and helper scripts in the directory as well.

:::::::::::::::::
Setup Simulation
:::::::::::::::::

At this point, all components and drivers should be added to the repository, and any makefiles modified or created (see :ref:`makefile section <comp_makefile_sec>` of component writing guide).  You are now ready to set up the execution environment, build the IPS, and prepare the input and configuration files.

^^^^^^^^^^^^^^^^^^^^^^
Execution Environment
^^^^^^^^^^^^^^^^^^^^^^

First, the platform on which to run the simulation must be determined.  When choosing a platform, take in to consideration:

  * The parallelism of the tasks you are running

    * Does your problem require 10s, 100s or 1000s of cores?
    * How well do your tasks take advantage of "many-core" nodes?

  * The location of the input files and executables

    * Does your input data exist on a suitable platform?
    * Is it reasonable to move the data to another machine?

  * Time and CPU hours

    * How much time will it take to run the set of simulations for the problem?  
    * Is there enough CPU time on the machine you want to use?

  * Dealing with results

    * Do you have access to enough hard drive space to store the output of the simulation until you have the time to analyze and condense it?

Once you have chosen a suitable platform, you may build the IPS like so::

  host ~ > cd <path to ips>
  host ips > . swim.bashrc.<machine_name>
  host ips > svn up
  host ips > make clean
  host ips > cp config/makeconfig.<machine_name> config/makeconfig.local
  host ips > make
  host ips > make install

Second, construct input files or edit the appropriate ones for your simulation.  This step is highly dependent on your simulation, but make sure that you check for the following things (and recheck after constructing the configuration file!):

  * Does each component have all the input files it needs?
  * Are there any global initial files, and are they present?  (This includes any plasma state and non-plasma state files.)
  * For each component input file: Are the values present, valid, and consistent?
  * For the collection of files for each component: Are the values present, valid, and consistent?
  * For the collection of files for each simulation: Are the values present, valid, and consistent?
  * Do the components model all of the targeted domain and phenomena of the experiment?
  * Does the driver use the components you expect? 
  * Does the driver implement the data dependencies between the components as you wish?

Third, you must construct the configuration file.  It is helpful to start with a configuration file that is related to the experiment you are working on, or you may start from the example configuration file, and edit it from there.  Some configuration file values are user specific, some are platform specific, and others are simulation or component specific.  It may be helpful to save your personal versions on each machine in your home directory or some other persistent storage location for reuse and editing.  These tend not to be good files to keep in subversion, however there are some examples in the example directory to get you started.  The most common and required configuration file entries are explained here.  For more a more complete description of the configuration options, see :doc:`The Configuration File - Explained<config_file>`.

* User Data Section::

    USER_W3_DIR = <location of your web directory on this platform>
    USER_W3_BASEURL = <URL of your space on the portal>
    USER = <user name>          # Optional, if missing the unix username is used 
  
  Set these values to the www directory you created for your own runs, a matching url for the portal to store your run info, and your user name (this is used on the portal to identify simulations you run).  These should be the same for all of your runs on a given platform.

* Simulation Info Section::

    RUN_ID = <short name of run>
    TOKAMAK_ID = <name of the tokamak>
    SHOT_NUMBER = 1
    ...
    SIM_NAME = ${RUN_ID}_${SHOT_NUMBER}

    OUTPUT_PREFIX =

    IPS_ROOT = <location of built ips>
    SIM_ROOT = <location of output tree>

    RUN_COMMENT = <used by portal to help identify what ran and why>
    TAG = <grouping string>
    ...
    SIMULATION_MODE = NORMAL
    RESTART_TIME =
    RESTART_ROOT = ${SIM_ROOT}

  In this section the simulation is described and key locations are specified.  *RUN_COMMENT* and *TAG*, along with *RUN_ID*, *TOKAMAK_ID*, and *SHOT_NUMBER* are used by the portal to describe this simulation.  *RUN_ID*, *TOKAMAK_ID*, and *SHOT_NUMBER* are commonly used to construct the *SIM_NAME*, which is often used in as the directory name of the *SIM_ROOT*.  The *IPS_ROOT* is the top-level of the IPS source tree that you are using to execute this simulation.  And finally, the *SIMULATION_MODE* and related items identify the simulation as a *NORMAL* or *RESTART* run.

* Logging Section::

    LOG_FILE = ${RUN_ID}_sim.log
    LOG_LEVEL = DEBUG | WARN | INFO | CRITICAL

  The logging section defines the name of the log file and the default level of logging for the simulation.  The log file for the simulation will contain all logging messages generated by the components in this simulation.  Logging messages from the framework and services will be written to the framework log file.  The *LOG_LEVEL* may be the following and may differ from the framework log level (in order of most verbose to least) [#]_: 
  
  * *DEBUG* - all messages are produced, including debugging messages to help diagnose problems.  Use this setting for debugging runs only.
  * *INFO* - these are messages stating what is happening, as opposed to what is going wrong.  Use this logging level to get an idea of how the different pieces of the simulation interact, without extraneous messages from the debugging level.
  * *WARN* - these messages are produced when the framework or component expects different conditions, but has an alternative behavior or default value that is also valid.  In most cases these messages are harmless, but may indicate a behavior that is different than expected.  This is the most common logging level.
  * *ERROR* - conditions that throw exceptions typically also produce an error message through the logging mechanism, however not all errors result in the failure of a component or the framework.
  * *CRITICAL* - only messages about fatal errors are produced.  Use this level when using a well known and reliable simulation.

* Plasma State Section::

    PLASMA_STATE_WORK_DIR = ${SIM_ROOT}/work/plasma_state

    # Config variables defining simulation specific names for plasma state files    
    CURRENT_STATE = ${SIM_NAME}_ps.cdf
    PRIOR_STATE = ${SIM_NAME}_psp.cdf
    NEXT_STATE = ${SIM_NAME}_psn.cdf
    CURRENT_EQDSK = ${SIM_NAME}_ps.geq
    CURRENT_CQL = ${SIM_NAME}_ps_CQL.dat
    CURRENT_DQL = ${SIM_NAME}_ps_DQL.nc
    CURRENT_JSDSK = ${SIM_NAME}_ps.jso

    # List of files that constitute the plasma state              
    PLASMA_STATE_FILES1 = ${CURRENT_STATE} ${PRIOR_STATE} ${NEXT_STATE} ${CURRENT_EQDSK}
    PLASMA_STATE_FILES2 = ${CURRENT_CQL} ${CURRENT_DQL} ${CURRENT_JSDSK}
    PLASMA_STATE_FILES = ${PLASMA_STATE_FILES1} ${PLASMA_STATE_FILES2}


  Specifies the naming convention for the plasma state files so the framework and components can manipulate and reference them in the config file and during execution.  The initial file locations are also specified here.

* Ports Section::

    [PORTS]
        NAMES = INIT DRIVER MONITOR EPA RF_IC NB FUS

    # Required ports - DRIVER and INIT       
        [[DRIVER]]
            IMPLEMENTATION = GENERIC_DRIVER

        [[INIT]]
            IMPLEMENTATION = minimal_state_init
    # Physics ports                                                                
       [[RF_IC]]
           IMPLEMENTATION = model_RF_IC

       [[FP]]
           IMPLEMENTATION = minority_model_FP

       [[FUS]]
           IMPLEMENTATION = model_FUS

       [[NB]]
           IMPLEMENTATION = model_NB

       [[EPA]]
           IMPLEMENTATION = model_EPA

       [[MONITOR]]
           IMPLEMENTATION = monitor_comp_4

  The ports section specifies which ports are included in the simulation and which implementation of the port is to be used.  Note that a *DRIVER* must be specified, and a warning will be issued if there is no *INIT* component present at start up.  The value of *IMPLEMENTATION* for a given port *must* correspond to a component description below.

* Component Configuration Section::

    [<component name>]
        CLASS = <port name>
        SUB_CLASS = <type of component>
        NAME = <class name of component implementation>
        NPROC = <# of procs for task invocations>
        BIN_PATH = ${IPS_ROOT}/bin
        INPUT_DIR = ${DATA_TREE_ROOT}/<location of input directory>
            INPUT_FILES = <input files for each step>
            OUTPUT_FILES = <output files to be archived>
            PLASMA_STATE_FILES = ${CURRENT_STATE} ${NEXT_STATE} ${CURRENT_EQDSK}
            RESTART_FILES = ${INPUT_FILES} <extra state files>
        SCRIPT = ${BIN_PATH}/<component implementation>

  For each component, fill in or modify the entry to match the locations of the input, output, plasma state, and script locations.  Also, be sure to check the *NPROC* entry to suit the problem size and scalability of the executable, and add any component specific entries that the component implementation calls for.  The data tree is a SWIM-public area where simulation input data can be stored.  It allows multiple users to access the same data and have reasonable assurance that they are indeed using the same versions.  On franklin the data tree root is ``/project/projectdirs/m876/data/``, and on stix it is ``/p/swim1/data/``.  The plasma state files must be part of the simulation plasma state.  It may be a subset if there are files that are not needed by the component on each step.  Additional component-specific entries can also appear here to signal a piece of logic or set a data value.

* Checkpoint Section::

    [CHECKPOINT]
       MODE = WALLTIME_REGULAR
       WALLTIME_INTERVAL = 15
       NUM_CHECKPOINT = 2
       PROTECT_FREQUENCY = 5

This section specifies the checkpoint policy you would like enforced for this simulation, and the corresponding parameters to control the frequency and number of checkpoints taken.  See the comments in the same configuration file or the configuration file :doc:`documentation <config_file>`.  If you are debugging or running a component or simulation for the first time, it is a good idea to take frequent checkpoints until you are confident that the simulation will run properly.

* Time Loop Section::

    [TIME_LOOP]
        MODE = REGULAR
        START = 0.0
        FINISH = 20.0
        NSTEP = 5

  This section sets up the time loop to help the driver manage the time progression of the simulation.  If you are debugging or running a component or simulation for the first time, it is a good idea to take very few steps until you are confident that the simulation will run properly.

Lastly, double-check that your input files and config file are both self-consistent and make physics sense.

.. [#] For more information and guidance about how the Python logging module works, see the Python logging module `tutorial  <http://docs.python.org/howto/logging.html>`_.

::::::::::::::::::::::::::::::::::
Run Simulation
::::::::::::::::::::::::::::::::::

Now, that you have everything set up, it is time to construct the batch script to launch the IPS.  Just like the configuration files, this is something that tends to be user specific and platform specific, so it is a good idea to keep local copy in a persistant directory on each platform you tend to use for easy modification.

As an example, here is a skeleton of a batch script for Franklin::

  #! /bin/bash
  #PBS -A <project code for accounting>
  #PBS -N <name of simulation>
  #PBS -j oe                            # joins stdout and stderr
  #PBS -l walltime=0:6:00
  #PBS -l mppwidth=<number of *cores* needed>
  #PBS -q <queue to submit job to>
  #PBS -S /bin/bash                                               
  #PBS -V                                                              

  IPS_ROOT=<location of IPS root>
  cd $PBS_O_WORKDIR
  umask=0222

  $IPS_ROOT/bin/ips [--config=<config file>]+ \  
    		     --platform=$IPS_ROOT/franklin.conf \
		     --log=<name of log file> \
		    [--debug]  \
		    [--nodes=<number of nodes in this allocation>] \
		    [--ppn=<number of processes per node for this allocation>] 

Note that you can only run one instance of the IPS per batch submission, however you may run multiple simulations in the same batch allocation by specifying multiple ``--config=<config file>`` entries on the command line.  Each config file must have a unique file name, and *SIM_ROOT*.  The different simulations will share the resources in the allocation, in many cases improving the resource efficiency, however this may make the execution time of each individual simulation a bit longer due to waiting on resources.

The IPS also needs information about the platform it is running on (``--platform=$IPS_ROOT/franklin.conf``) and a log file (``--logfile=<name of log file>``)for the framework output.  Platform files for commonly used platforms are provided in the top-level of the ips directory.  It is strongly recommended that you use the appropriate one for launching IPS runs.  See :doc:`platform` for more information on how to use or create these files.

Lastly, there are some optional command line arguments that you may use.  ``--debug`` will turn on debugging information from the framework.  ``--nodes`` and ``--ppn`` allow the user to manually set the number of nodes and processes per node for the framework.  This will override any detection by the framework and should be used with caution.  It is, however, a convenient way to run the ips on a machine without a batch scheduler. 

Once your job is running, you can watch their progress on the `portal  <http://swim.gat.com:8080/display/>`_.  Note that each *simulation* will appear on the portal, so multiple simulation jobs will look like multiple simulations that all started around the same time.

::::::::::::::::::::::::::::::::::
Analysis and/or Debugging
::::::::::::::::::::::::::::::::::

Once your run (or set of runs) is done, it is time to look at the output.  First, we will examine the structure of the output tree:

  *${SIM_ROOT}/*

    *${PORTAL_RUNID}*

      File containing the portal run ids that are associated with this directory.  There can be more than one.

    *<platform config file>*

    *<simulation configuration files>*
   
      Each simulation configuration file that used this sim root.

    *restart/*

      *<each checkpoint>/*

        *<each component>/*

          Directory containing the restart files for this checkpoint

    *simulation_log/*

      Directory containing the event log for each runid.

    *simulation_results/*
    
      *<each time step>/*

        *components/*
	
	  *<each component>/*

	    Directory containing the output files for the given component at the given step.

      *<each component>/*

        Directory containing the output files for each step.  File names are appended with the time step to avoid collisions. 

    *simulation_setup/*

      *<each component>/*

        Directory containing the input files from the beginning of the simulation.

    *work/*

      *<each component>/*

        Directory where the component computes from time step to time step.  Leftover input and output files from the last step will be present at the end of the simulation.

There are a few tools for visualizing (and light analysis) of a run or set of runs:

* Portal web interface to PCMF: This tool is a web interface to the PCMF tool (see below).  It has recently been integrated into the portal for quick and remote viewing.  For more in depth analysis, viewing and printing of graphs from the monitor component, use the more powerful standalone version of PCMF.
* PCMF: A tool to Plot and Compare multiple Monitor Files (``ips/components/monitor/monitor_4/PCMF.py``) is the local Python version of the web tool.  It uses Matplotlib to generate plots of the different values in the plasma state over the course of the simulation.  It also allows you to generate graphs for more than one set of monitor files.  Examples and instructions are located in the repo and are coming soon to this documentation.
* ELVis: This tool graphs values from netCDF (plasma state) files through a web browser plugin or using the Java client.

Using these utilities, your own scripts or manual inspection results can be analyzed, or bugs found.  Debugging a coupled simulation is more complicated than debugging a standalone code.  Here are some things to consider when a problem is encountered:

* Problems using the framework

  * Was an exception thrown?  If so, what was it and where did it come from?  If you don't understand the exception, talk to a framework developer.
  * Was something missing in the configuration file?
  * Were the components invoked and tasks launched as expected?
  * Did you use the proper implementation of the component and executable?
  * Was your compute environment/permissions/batch allocation set up properly?

* Data between components

  * Does each component update all the values in the plasma state it needs to?
  * Does each component update all output files it uses internally properly?
  * Are the components updating the plasma state in the right order?

* Physics code problem

  * Did a task return an error code?
  * Does the component check for a bad return code and handle it properly?
  * Is the code that is launched have the proper command line arguments?
  * Are the input and output files properly adapted to the executable?
  * Does the executable fail in standalone mode?
  * Was the executable built properly?
  * Were all necessary input and source files found?

If you are working out a problem, it is always good to:

* Turn on debugging output using the ``--debug`` flag on the command line, and setting the LOG_LEVEL in the configuration file to DEBUG.
* Turn on debugging output in physics codes to see what is going on during each task.
* Use frequent checkpoints to restart close to where the problem starts.
* Reduce the number of time steps to the minimum needed to produce the problem.
* Only change one thing before rerunning the simulation to determine what fixes the problem.

