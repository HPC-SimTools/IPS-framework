Developing Drivers and Components for IPS Simulations
=====================================================

This section is for those who wish to modify and write drivers and components to construct a new simulation scenario.  It is expected that readers are familiar with IPS terminology, the directory structure and have looked at some existing drivers and components before attempting to modify or create new ones.  This guide will describe the elements of a simulation, how they work together, the structure of drivers and components, IPS services API, and a discussion of control flow, data flow and fault management. 

--------------------------
Elements of a Simulation
--------------------------

When constructing a new simulation scenario, writing a new component or even making small modifications to existing components and drivers, it is important to consider and understand how the pieces of an IPS simulation work together.  An IPS simulation scenario is specified in the *configuration file*.  This file tells the framework how to set up the output tree for the data files, which components are needed and where the implementation is located, time loop and checkpoint parameters, and input and output files for each component and the simulation as a whole are specified.  The *framework* uses this information to find the pieces of code and data that come together to form the simulation, as well as provide this information to the components and driver to manage the simulation and execution of tasks [#]_.

The framework provides *services* that are used by components to perform data, task, resource and configuration management, and provides an event service for exchanging messages with internal and external entities.  While these services are provided as a single API to component writers, the documentation (and underlying implementation) divides them into groups of methods to perform related actions.  *Data management* services include staging input, output and plasma state files, changing directories, and saving task restart files, among others.  The framework will perform these actions for the calling component based on the files specified in the configuration file and within the method call maintaining coherent directory spaces for each component's work, previous steps, checkpoints and globally accessible data to insure that name collisions do not corrupt data and that global files are accessed in a well-defined manner [#]_.  Services for *task management* include methods for component method invocations, or *calls*, and executable launch on compute nodes, or *task launches*.  The task management portion of the framework works in conjunction with the IPS resource manager to execute multiple parallel executables within a single batch allocation, allowing IPS simulations to efficiently utilize compute resources, as data dependencies allow.  The IPS task manager provides blocking and non-blocking versions of ``call`` and ``launch_task``, including a notion of *task pools* and the ability to wait for the completion of any or all calls or tasks in a group.  These different invocation and launch methods allow a component writer to manage the control flow and implement data dependencies between components and tasks.  This task management interface hides the resource management, platform specific, task scheduling, and process interactions that are performed by the framework, allowing component writers to express their simulations and component coupling more simply.  The *configuration manager* primarily reads the configuration file and instantiates the components for the simulation so that they can interact over the course of the simulation.  It also provides an interface for accessing key data elements from the configuration file, such as the time loop, handles to components and any component specific items listed in the configuration file.

--------------------------
Components
--------------------------

There are three classes of components: framework, driver, and general purpose (physics components fall into this category).  In the IPS, each component executes in a separate process (a child of the framework) and implements the following methods:

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

The component writer will use the services API to help perform data, task, configuration and event management activities to implement these methods.

This document focuses on helping (physics) component and driver writers successfully write new components.  It will take the writer step-by-step through the process of writing basic components.

.. [#] Tasks are the binaries that are launched by components on compute nodes, where as components are Python scripts that manage the data movements and execution of the tasks (with the help of IPS services).  In general, the component is aware of the driver and its existence within a coupled simulation, and the task does not.

.. [#] The IPS uses an agreed upon file format and associated library to manage global (shared) data for the simulation, called the Plasma State.  It is made up of a set of netCDF files with a defined layout so that codes can access and share the data.  At the beginning of each step the component will get a local copy of the current plasma state, execute based on these values, and then update the plasma state values that it changed to the global copy.  There are data management services to perform these actions, see :ref:`Data Management API <data-mgmt-api>`.


--------------------
Writing Components
--------------------

In this section, we take you through the steps of adding a new component to the IPS landscape.  It will cover where to put source code, scripts, binaries and inputs, how to construct the component, how to add the component to the IPS build system, and some tips to make this process smoother.

^^^^^^^^^^^^^^^^^^^^^
Adding a New Binary
^^^^^^^^^^^^^^^^^^^^^

The location of the binary does not technically matter to the framework, as long as the path can be constructed by the component and the permissions are set properly to launch it when the time comes.  There are two recommended ways to express the location of the binary to the component:

1.  For stable and shared binaries, the convention is to put them in the platform's *PHYS_BIN*.  This way, the *PHYS_BIN* is specified in the platform configuration file and the component can access the location of the binary relative to that location on each machine.  See :doc:`Platforms and Platform Configuration<platform>`.

2. The location of the binary is specified in the component's section of the simulation configuration file.  This way, the binary can be specified just before runtime and the component can access it through the framework services.  This convention is typically used during testing, experimentation with new features in the code, or other circumstances where the binary may not be stable, fully compatible with other components, or ready to be shared widely.

^^^^^^^^^^^^^^^^^^^^^^^^^
Data Coupling Preparation
^^^^^^^^^^^^^^^^^^^^^^^^^

Once you have your binary built properly and available, it is time to work on the data coupling to the other components in a simulation.  This is a component specific task, but it often takes conversation with the other physicists in the group as to what values need to be communicated and to develop an understanding of how they are used.

When the physics of interest is identified, adapters need to be written to translate IPS-style inputs (from the Plasma State) to the inputs the binary is expecting, and a similar adapter for the output files.

^^^^^^^^^^^^^^^^^^^^^
Create a Component
^^^^^^^^^^^^^^^^^^^^^

Now it is time to start writing the component.  At this point you should have an idea of how the component will fit into a coupled simulation and the types of activities that will need to happen during the *init*, *step*, and *finalize* phases of execution.

1. Create a directory for your component (if you haven't already). The convention in the IPS repository is to put component scripts and helpers in ``ips/components/<port_name>/<component_name>``, where *port_name* is the "type" of component, and the *component_name* is the implementation of that "type" of component.  Often, *component_name* will contain the name of the code it executes.  If there is already a component directory and existing components, then you may want to make your own directory within the existing component's directory or just add your component in that same directory.

2. Copy the skeleton component (``ips/doc/examples/skeleton_comp.py``) to the directory you choose or created.  Be sure to name it such that others will easily know what the component does. For example, a component for TORIC, a code that models radio frequency heating in plasmas, is found in ``ips/components/rf/toric/`` and called ``rf_ic_toric_mcmd.py``.

3. Edit skeleton.  Components should be written such that the inputs, outputs, binaries and other parameters are specified in the configuration file or appear in predictable locations *across platforms*.  The skeleton contains an outline, in comments, of the activities that a generic component does in each method invocation.  You will need to fill in the outline with your own calls to the services and any additional activities in the appropriate places.  Take a look at the other example components in the ``ips/doc/examples/`` or ``ips/components/`` for guidance.  The following is an outline of the changes that need to be made:

   a. Change the name of the class and update the file to use that name every where it says ``# CHANGE EXAMPLE TO COMPONENT NAME``.
   b. Modify ``init`` to initialize the input files that are needed for the first step.  Update shared files as needed.
   c. Modify ``step`` to use the appropriate *prepare_input* and *process_output* executables.  Make sure all shared files that are changed during the course of the task execution are saved to their proper locations for use by other components.  Make sure that all output files that are needed for the next step are copied to archival location.  If a different task launch mechanism is required, modify as needed.  See :ref:`Task Launch API<task-launch-api>` for related services.
   d. Modify ``finalize`` to do any clean up as needed.
   e. Modify ``checkpoint`` to save all files that are needed to restart from later.
   f. Modify ``restart`` to set up the component to resume computation from a checkpointed step.

While writing your component, be sure to use ``try...except`` blocks [#]_ to catch problems and the services logging mechanisms to report critical errors, warnings, info and debug messages.  It is *strongly* recommended that you use exceptions and the services logging capability for debugging and output.  Not catching exceptions in the component can lead to the driver or framework catching them in a weird place and it will likely take a long time to track down where the problem occurred.  The logging mechanism in the IPS provides time stamps of when the event occurred, the component that produced the message, as well as a nice way to format the message information.  These messages are written to the log file (specified in the configuration file for the simulation) atomically, unlike normal print statements.  Absolute ordering is not guaranteed across different components, but ordering within the same component is guaranteed.  See :ref:`Logging API<logging-api>` for more information on when to use the different logging levels.

At this point, it might be a good idea to start the documentation of the component in ``ips/doc/component_guides/``.  You will find a *README* file in ``ips/doc/`` that explains how to build and write IPS documentation, and another in the ``ips/doc/component_guides/`` on what information to include in your component documentation.

.. [#] `Tutorial on exceptions <http://docs.python.org/tutorial/errors.html>`_

.. _comp_makefile_sec:

:::::::::::::::
Makefile
:::::::::::::::

Once you are satisfied with the implementation of the component, it is time to construct and edit the Makefiles such that the component is built properly by the framework.  The Makefile will build your executables and move scripts to ``${IPS_ROOT}/bin``.

1. If you do not already have a makefile in the directory for your new component, copy the examples (``ips/doc/examples/Makefile`` and ``ips/doc/examples/Makefile.include``) to your component directory.

2. List all executables to be compiled in *EXECUTABLES* and scripts in *SCRIPTS*. ::

     EXECUTABLES = do_toric_init prepare_toric_input process_toric_output \
		     process_toric_output_mcmd # Ptoric.e Storic.e
     SCRIPTS = rf_ic_toric.py rf_ic_toric_mcmd.py
     TARGETS = $(EXECUTABLES)

3. Make targets for each executable.  Do not remove targets *all*, *install*, *clean*, *distclean*, and *.depend*.

4. Add any libraries that are needed to ``ips/config/makeconfig.local``. (This is where *LIBS* and the various fortran flags are defined.)

5. Add component to top-level Makefile.  Toric example::

     TORIC_COMP_DIR=components/rf/toric/src
     TORIC_COMP=.TORIC

6. Add component dir to *COMPONENT_DIRS*::

     COMPONENTS_DIRS=$(AORSA_COMP_DIR) \
                     $(TORIC_COMP_DIR) \
                     $(BERRY_INIT_COMP_DIR) \
                     $(CHANGE_POWER_COMP_DIR) \
                     $(BERRY_CQL3D_INIT_COMP_DIR) \
                     $(CHANGE_POWER_COMP_DIR) \
                     $(CQL3D_COMP_DIR) \
                     $(ELWASIF_DRIVER_COMP_DIR) \
                     ...

7. Add component to *COMPONENTS*::

     COMPONENTS=$(AORSA_COMP) \
                $(TORIC_COMP) \
                $(BERRY_AORSA_INIT_COMP) \
                $(BERRY_CQL3D_INIT_COMP) \
                $(CHANGE_POWER_COMP) \
                $(CQL3D_COMP) \
                $(BERRY_INIT_COMP) \
                $(ELWASIF_DRIVER_COMP) \
                ...

Now you should be able to build the IPS with your new component.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Testing and Debugging a Component
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now it is time to construct a simulation to test your new component.  There are two ways to test a new component.  The first is to have the IPS just run that single component without a driver, by specifying your component as the driver.  The second is to plug it into an existing driver.  The former will test only the task launching and data movement capabilities.  The latter can also test the data coupling and call interface to the component.  This section will describe how to xstest your component using an existing driver (including how to add the new component to the driver).

As you can see in the example component, almost everything is specified in the configuration file and read at run-time.  This means that the configuration of components is vitally important to their success or failure.  The entries in the component configuration section are made available to the component automatically, thus a component can access them by *self.<entry_name>*.  This is useful in many cases, and you can see in the example component that *self.NPROC* and *self.BIN_PATH* are used.  Global configuration parameters can also be accessed using services call *get_config_param(<param_name>)* (:ref:`API<misc-api>`).

Drivers access components by their port names (as specified in the configuration file).  To add a new component to the driver you will either need to add a new port name or use an existing port name.   ``ips/components/drivers/dbb/generic_driver.py`` is a good all-purpose driver that most components should be able to use.  If you are using an existing port name, then the code should just work.  It is recommended to go through the driver code to make sure the component is being used in the expected manner.  To add a new port name, you will need to add code to *generic_driver.step()*:

* get a reference to the port (*self.services.get_port(<name of port>)*)
* call "init" on that component (*self.services.call(comp_ref, "init")*) 
* call "step" on that component (*self.services.call(comp_ref, "step")*)
* call "finalize" on that component (*self.services.call(comp_ref, "finalize")*)

The following sections of the configuration file may need to be modified.  If you are not adding the component to an existing simulation, you can copy a configuration file from the examples directory and modify it.

1. *Plasma State (Shared Files) Section*
   
   You will need to modify this section to include any additional files needed by your component::

      # Where to put plasma state files as the simulation evolves
      STATE_WORK_DIR = ${SIM_ROOT}/work/plasma_state
      CURRENT_STATE = ${SIM_NAME}_ps.cdf
      PRIOR_STATE = ${SIM_NAME}_psp.cdf
      NEXT_STATE = ${SIM_NAME}_psn.cdf
      CURRENT_EQDSK = ${SIM_NAME}_ps.geq
      CURRENT_CQL = ${SIM_NAME}_ps_CQL.nc
      CURRENT_DQL = ${SIM_NAME}_ps_DQL.nc
      CURRENT_JSDSK = ${RUN_ID}_ps.jso

      # What files constitute the plasma state
      STATE_FILES1 = ${CURRENT_STATE} ${PRIOR_STATE}
      			    ${NEXT_STATE}
      STATE_FILES2 = ${STATE_FILES1}  ${CURRENT_EQDSK}
      			    ${CURRENT_CQL} ${CURRENT_DQL}
      STATE_FILES = ${STATE_FILES2}  ${CURRENT_JSDSK}

2. *Ports Section*

   You will need to add the component to the ports section so that it can be properly detected by the framework and driver.  An entry for *DRIVER* must be specified, otherwise the framework will abort.  Also, a warning is produced if there is no *INIT* component.  Note that all components added to the *NAMES* field must have a corresponding subsection. ::

     [PORTS]
         NAMES = INIT DRIVER MONITOR EPA NB
        [[DRIVER]]                               
             IMPLEMENTATION = EPA_IC_FP_NB_DRIVER
         [[INIT]]                                      
             IMPLEMENTATION = minimal_state_init
         [[RF_IC]]
             IMPLEMENTATION = model_RF_IC

         ...

3. *Component Description Section*

   The ports section just defines which components are going to be used in this simulation, and point to the section where they are described.  The component description section is where those definitions take place::

     [TSC]
         CLASS = epa
         SUB_CLASS =
         NAME = tsc
         NPROC = 1
         BIN_PATH = ${IPS_ROOT}/bin
         INPUT_DIR = ${IPS_ROOT}/components/epa/tsc
         INPUT_FILES = inputa.I09001 sprsina.I09001config_nbi_ITER.dat
         OUTPUT_FILES = outputa tsc.cgm inputa log.tsc ${STATE_FILES}
         SCRIPT = ${BIN_PATH}/epa_nb_iter.py

   The component section starts with a label that matches what is listed as the implementation in the ports section.  These *must* match or else the framework will not find your component and the simulation will fail before it starts (or worse, use the wrong implementation!). *CLASS* and *SUBCLASS* typically refer to the directory hierarchy and are sometimes used to identify the location of the source code and input files.  Note that *NAME* must match the python class name that implements the component.  *NPROC* is the number of *processes* that the binary needs to use when launched on compute nodes.  The *BIN_PATH* will almost always be ``${IPS_ROOT}/bin`` and refers to the location of any binaries you wish to use in your component.  The Makefile will move your component script to ``${IPS_ROOT}/bin`` when you build the IPS, and should do the same to any binaries that are produced from the targets in the Makefile.  If you have pre-built binaries that exist in another location, an additional entry in the component description section may be a convenient place to put it.  *INPUT_DIR*, *INPUT_FILES* and *OUTPUT_FILES* specify the location and names of the input and output files, respectively.  If a subset of plasma states files is all that is required by the component, they are specified here (*STATE_FILES*).  If the entry is omitted, *all* of the plasma state files are used.  This prevents the full set of files to be copied to and from the component's work directory on every step, saving time and space.  Lastly, *SCRIPT* is the Python script that contains the component code, specifically the Python class in *NAME*.  Additionally, any component specific values maybe specified here to control logic or set data values that change often.

4. *Time Loop Section*

   This may need to be modified for your component or the driver that uses your new component.  During testing, a small number of steps is appropriate. ::

      # Time loop specification (two modes for now) EXPLICIT | REGULAR
      # For MODE = REGULAR, the framework uses the variables START, FINISH, and NSTEP
      # For MODE = EXPLICIT, the framework uses the variable VALUES (space separated 
      # list of time values) 
      [TIME_LOOP]
          MODE = EXPLICIT
          VALUES = 75.000 75.025 75.050 75.075 75.100 75.125


^^^^^^^^^^^^^^^^^^^^^^^
Tips
^^^^^^^^^^^^^^^^^^^^^^^

This section contains some useful tips on testing, debugging and documenting your new component.

* General:

  * Naming is important.  You do not want the name of your component to overlap with another, so make sure it is unique.
  * Be sure to commit all the files and directories that are needed to build and run your component.  This means the executables, Makefiles, component script, helper scripts and input files.

* Testing:

  * To test a new component, first run it as the driver component of a simulation all by itself.  This will make sure that the component itself works with the framework.
  * The next step is to have a driver call just your new component to make sure it can be discovered and called by the driver properly.
  * The next step is to determine if the component can exchange global data with another component.  To do this run two components in a driver and verify they are exchanging data properly.
  * When testing IPS components and simulations, it may be useful to turn on debugging information in the IPS and the underlying executables.
  * If this is a time stepping simulation, a small number of steps is useful because it will lead to shorter running times, allowing you to submit the job to a debug or other faster turnaround queue.

* Debugging:
  
  * Add logging messages (*services.info()*, *services.warning()*, etc.) to make sure your component does what you think it does.
  * Remove other components from the simulation to figure out which one or which interaction is causing the problem
  * Take many checkpoints around the problem to narrow in on the problem.
  * Remove concurrency to see if one component is overwriting another's data.

* Documentation:

  * Document the component code such that another person can understand how it works.  It helps if the structure remains the same as the example component.
  * Write a description of what the component does, the inputs it uses, outputs it produces, and what scenarios and modes it can be used in in the component documentation section.


-----------------
Writing Drivers
-----------------

The driver of the simulation manages the control flow and synchronization across components via time stepping or implicit means, thus orchestrating the simulation.  There is only one driver per simulation and it is invoked by the framework and is responsible for invoking the components that make up the simulation scenario it implements.  It is also responsible for managing data at the simulation level, including checkpoint and restart activities.

Before writing a driver, it is a good idea to have the components already written.  Once the components that are to be used are chosen the data coupling and control flow must be addressed.

In order to couple components, the data that must be exchanged between them and the ordering of updates to the plasma state must be determined.  Once the data dependencies are identified (which components have to run before the next, and which ones can run at the same time).  You can write the body of the driver.  Before going through the steps of writing a driver, review the :ref:`method invocation API <comp-invocation-api>` and plan which methods to use during the main time loop.

The framework will invoke the methods of the *INIT* and *DRIVER* components over the course of the simulation, defining the execution of the run:

* ``init_comp.init()`` - initialization of initialization component
* ``init_comp.step()`` - execution of initialization work
* ``init_comp.finalize()`` - cleanup and confirmation of initialization
* ``driver.init()`` - any initialization work (typically empty)
* ``driver.step()`` - the bulk of the simulation
  
  * get references to the ports
  * call *init* on each port
  * get the time loop
  * implement logic of time stepping
  * during each time step:

    * perform pre-step logic that may stage data or determine which components need to run or what parameters are given to each component    
    * call *step* on each port (as appropriate)
    * manage global plasma state at the end of each step
    * checkpoint components (frequency of checkpoints is controlled by framework)

  * call *finalize* on each component  

* ``driver.finalize()`` - any clean up activities (typically empty)

It is recommended that you start with the ``ips/components/drivers/dbb/generic_driver.py`` and modify it as needed.  You will most likely be changing: how the components are called in the main loop (the generic driver calls each component in sequence), the pre-step logic phase, and what ports are used.  The data management and checkpointing calls should remain unchanged as their behavior is controlled in the configuration file.

The process for adding a new driver to the IPS is the same as that for the component.  See the appropriate sections above for adding a component.




.. _api_section:

-----------------
IPS Services API
-----------------

The IPS framework contains a set of managers that perform services for the components.  A component uses the services API to access them, thus hiding the complexity of the framework implementation.  Below are descriptions of the individual function calls grouped by type.  To call any of these functions in a component replace *ServicesProxy* with *self.services*.  The *services* object is passed to the component upon creation by the framework.

.. _comp-invocation-api:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Component Invocation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Component invocation in the IPS means one component is calling another component's function.  This API provides a mechanism to invoke methods on components through the framework.  There are blocking and non-blocking versions, where the non-blocking versions require a second function to check the status of the call.  Note that the *wait_call* has an optional argument (*block*) that changes when and what it returns. 

.. automethod:: ipsframework.services.ServicesProxy.call
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.call_nonblocking
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.wait_call
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.wait_call_list
   :noindex:

.. _task-launch-api:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Task Launch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The task launch interface allows components to launch and manage the execution of (parallel) executables.  Similar to the component invocation interface, the behavior of *launch_task* and the *wait_task* variants are controlled using the *block* keyword argument and different interfaces to *wait_task*.

.. automethod:: ipsframework.services.ServicesProxy.launch_task
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.wait_task
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.wait_task_nonblocking
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.wait_tasklist
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.kill_task
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.kill_all_tasks
   :noindex:

The task pool interface is designed for running a group of tasks that are independent of each other and can run concurrently.  The services manage the execution of the tasks efficiently for the component.  Users must first create an empty task pool, then add tasks to it.  The tasks are submitted as a group and checked on as a group.  This interface is basically a wrapper around the interface above for convenience.

.. automethod:: ipsframework.services.ServicesProxy.create_task_pool
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.add_task
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.submit_tasks
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.get_finished_tasks
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.remove_task_pool
   :noindex:

.. _misc-api:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Miscellaneous
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following services do not fit neatly into any of the other categories, but are important to the execution of the simulation.

.. automethod:: ipsframework.services.ServicesProxy.get_working_dir
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.update_time_stamp
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.send_portal_event
   :noindex:

.. _data-mgmt-api:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Data Management
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The data management services are used by the components to manage the data needed and produced by each step, and for the driver to manage the overall simulation data.  There are methods for component local, and simulation global files, as well as replay component file movements.  Fault tolerance services are presented in another section.

Staging of local (non-shared) files:

.. automethod:: ipsframework.services.ServicesProxy.stage_input_files
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.stage_output_files
   :noindex:

Staging of global (plasma state) files:

.. automethod:: ipsframework.services.ServicesProxy.stage_state
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.update_state
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.merge_current_state
   :noindex:

Staging of replay files:

.. automethod:: ipsframework.services.ServicesProxy.stage_replay_output_files
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.stage_replay_plasma_files
   :noindex:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Configuration Parameter Access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These methods access information from the simulation configuration file.

.. automethod:: ipsframework.services.ServicesProxy.get_port
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.get_config_param
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.set_config_param
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.get_time_loop
   :noindex:

.. _logging-api:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Logging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following logging methods can be used to write logging messages to the simulation log file.  It is *strongly* recommended that these methods are used as opposed to print statements.  The logging capability adds a timestamp and identifies the component that generated the message.  The syntax for logging is a simple string or formatted string::

    self.services.info('beginning step')
    self.services.warning('unable to open log file %s for task %d, will use stdout instead', 
     	 		  logfile, task_id)

There is no need to include information about the component in the message as the IPS logging interface includes a time stamp and information about what component sent the message::

      2011-06-13 14:17:48,118 drivers_ssfoley_branch_test_driver_1 DEBUG    __initialize__(): <branch_testing.branch_test_driver object at 0xb600d0>  branch_testing_hopper@branch_test_driver@1
      2011-06-13 14:17:48,125 drivers_ssfoley_branch_test_driver_1 DEBUG    Working directory /scratch/scratchdirs/ssfoley/rm_dev/branch_testing_hopper/work/drivers_ssfoley_branch_test_driver_1 does not exist - will attempt creation
      2011-06-13 14:17:48,129 drivers_ssfoley_branch_test_driver_1 DEBUG    Running - CompID =  branch_testing_hopper@branch_test_driver@1
      2011-06-13 14:17:48,130 drivers_ssfoley_branch_test_driver_1 DEBUG    _init_event_service(): self.counter = 0 - <branch_testing.branch_test_driver object at 0xb600d0>
      2011-06-13 14:17:51,934 drivers_ssfoley_branch_test_driver_1 INFO     ('Received Message ',)
      2011-06-13 14:17:51,934 drivers_ssfoley_branch_test_driver_1 DEBUG    Calling method init args = (0,)
      2011-06-13 14:17:51,938 drivers_ssfoley_branch_test_driver_1 INFO     ('Received Message ',)
      2011-06-13 14:17:51,938 drivers_ssfoley_branch_test_driver_1 DEBUG    Calling method step args = (0,)
      2011-06-13 14:17:51,939 drivers_ssfoley_branch_test_driver_1 DEBUG    _invoke_service(): init_task  (48, 'hw', 0, True, True, True)
      2011-06-13 14:17:51,939 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|0)
      2011-06-13 14:17:51,952 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|0), response = <messages.ServiceResponseMessage object at 0xb60ad0>
      2011-06-13 14:17:51,954 drivers_ssfoley_branch_test_driver_1 DEBUG    Launching command : aprun -n 48 -N 24 -L 1087,1084 hw
      2011-06-13 14:17:51,961 drivers_ssfoley_branch_test_driver_1 DEBUG    _invoke_service(): getTopic  ('_IPS_MONITOR',)
      2011-06-13 14:17:51,962 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|1)
      2011-06-13 14:17:51,972 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|1), response = <messages.ServiceResponseMessage object at 0xb60b90>
      2011-06-13 14:17:51,972 drivers_ssfoley_branch_test_driver_1 DEBUG    _invoke_service(): sendEvent  ('_IPS_MONITOR', 'PORTAL_EVENT', {'sim_name': 'branch_testing_hopper', 'portal_data': {'comment': 'task_id = 1 , Tag = None , Target = aprun -n 48 -N 24 -L 1087,1084 hw ', 'code': 'drivers_ssfoley_branch_test_driver', 'ok': 'True', 'eventtype': 'IPS_LAUNCH_TASK', 'state': 'Running', 'walltime': '4.72'}})
      2011-06-13 14:17:51,973 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|2)
      2011-06-13 14:17:51,984 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|2), response = <messages.ServiceResponseMessage object at 0xb60d10>
      2011-06-13 14:17:51,987 drivers_ssfoley_branch_test_driver_1 DEBUG    _invoke_service(): getTopic  ('_IPS_MONITOR',)
      2011-06-13 14:17:51,988 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|3)
      2011-06-13 14:17:52,000 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|3), response = <messages.ServiceResponseMessage object at 0xb60890>
      2011-06-13 14:17:52,000 drivers_ssfoley_branch_test_driver_1 DEBUG    _invoke_service(): sendEvent  ('_IPS_MONITOR', 'PORTAL_EVENT', {'sim_name': 'branch_testing_hopper', 'portal_data': {'comment': 'task_id = 1  elapsed time = 0.00 S', 'code': 'drivers_ssfoley_branch_test_driver', 'ok': 'True', 'eventtype': 'IPS_TASK_END', 'state': 'Running', 'walltime': '4.75'}})
      2011-06-13 14:17:52,000 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|4)
      2011-06-13 14:17:52,012 drivers_ssfoley_branch_test_driver_1 DEBUG    _get_service_response(REQUEST|branch_testing_hopper@branch_test_driver@1|FRAMEWORK@Framework@0|4), response = <messages.ServiceResponseMessage object at 0xb60a90>
      2011-06-13 14:17:52,012 drivers_ssfoley_branch_test_driver_1 DEBUG    _invoke_service(): finish_task  (1L, 1)



The table below describes the levels of logging available and when to use each one.  These levels are also used to determine what messages are produced in the log file.  The default level is ``WARNING``, thus you will see ``WARNING``, ``ERROR`` and ``CRITICAL`` messages in the log file.

.. tabularcolumns: |l|p{0.7\columnwidth}|

+---------+----------------------------------------------------------+
|Level    |  When it’s used                                          |
+=========+==========================================================+
|DEBUG    | Detailed information, typically of interest only when    |
|	  | diagnosing problems.                                     |
+---------+----------------------------------------------------------+
|INFO     | Confirmation that things are working as expected.        |
+---------+----------------------------------------------------------+
|WARNING  | An indication that something unexpected happened, or     |
|	  | indicative of some problem in the near future (e.g.      |
|         | "disk space low").  The software is still working as     |
|         | expected.                                                |
+---------+----------------------------------------------------------+
|ERROR    | Due to a more serious problem, the software has not been |
|	  | able to perform some function.                           |
+---------+----------------------------------------------------------+
|CRITICAL | A serious error, indicating that the program itself may  |
|	  | be unable to continue running.                           |
+---------+----------------------------------------------------------+

For more information about the logging module and how to used it, see `Logging Tutorial <http://docs.python.org/howto/logging.html#logging-basic-tutorial>`_.

.. automethod:: ipsframework.services.ServicesProxy.log
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.debug
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.info
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.warning
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.error
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.exception
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.critical
   :noindex:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Fault Tolerance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The IPS provides services to checkpoint and restart a coupled simulation by calling the checkpoint and restart methods of each component and certain settings in the configuration file.  The driver can call *checkpoint_components*, which will invoke the checkpoint method on each component associated with the simulation.  The component's *checkpoint* method uses *save_restart_files* to save files needed by the component to restart from the same point in the simulation.  When the simulation is in restart mode, the *restart* method of the component is called to initialize the component, instead of the *init* method.  The *restart* component method uses the *get_restart_files* method to stage in inputs for continuing the simulation.

.. automethod:: ipsframework.services.ServicesProxy.save_restart_files
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.checkpoint_components
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.get_restart_files
   :noindex:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Event Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The event service interface is used to implement the web portal connection, as well as for components to communicate asynchronously.

.. automethod:: ipsframework.services.ServicesProxy.publish
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.subscribe
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.unsubscribe
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.process_events
   :noindex:
