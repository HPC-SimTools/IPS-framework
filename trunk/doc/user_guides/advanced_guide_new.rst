Developing Drivers and Components for IPS Simulations
=====================================================

This section is for those who wish to modify and write drivers and components to construct a new simulation scenario.  It is expected that readers are familiar with IPS terminology, the directory structure and have looked at some existing drivers and components before attempting to modify or create new ones.  This guide will describe the elements of a simulation, how they work together, the structure of drivers and components, IPS services API, and a discussion of control flow, data flow and fault management. 

--------------------------
Elements of a Simulation
--------------------------

When constructing a new simulation scenario, writing a new component or even making small modifications to existing components and drivers, it is important to consider and understand how the pieces of an IPS simulation work together.  An IPS simulation scenario is specified in the *configuration file*.  This file tells the framework how to set up the output tree for the data files, which components are needed and where the implementation is located, time loop and checkpoint parameters, and input and output files for each component and the simulation as a whole are specified.  The *framework* uses this information to find the pieces of code and data that come together to form the simulation, as well as provide this information to the components and driver to manage the simulation and execution of tasks [#]_.

The framework provides *services* that are used by components to perform data, task, resource and configuration management, and provides an event service for exchanging messages with internal and external entities.  While these services are provided as a single API to component writers, the documentation (and underlying implementation) divides them into groups of methods to perform related actions.  *Data management* services include staging input, output and plasma state files, changing directories, and saving task restart files, among others.  The framework will perform these actions for the calling component based on the files specified in the configuration file and within the method call maintaining coherent directory spaces for each component's work, previous steps, checkpoints and globally accessible data to insure that name collisions do not corrupt data and that global files are accessed in a well-defined manner [#]_.  

Services for *task management* include methods for component method invocations, or *calls*, and executable launch on compute nodes, or *task launches*.  The task management portion of the framework works in conjunction with the IPS resource manager to execute multiple parallel executables within a single batch allocation, allowing IPS simulations to efficiently utilize compute resources, as data dependencies allow.  The IPS task manager provides blocking and non-blocking versions of ``call`` and ``launch_task``, including a notion of *task pools* and the ability to wait for the completion of any or all calls or tasks in a group.  These different invocation and launch methods allow a component writer to manage the control flow and implement data dependencies between components and tasks.  

This task management interface hides the resource management, platform specific, task scheduling, and process interactions that are performed by the framework, allowing component writers to express their simulations and component coupling more simply.  The *configuration manager* primarily reads the configuration file and instantiates the components for the simulation so that they can interact over the course of the simulation.  It also provides an interface for accessing key data elements from the configuration file, such as the time loop, handles to components and any component specific items listed in the configuration file.

-----------------
Workflow Concepts
-----------------

The following sections provide descriptions for how to use IPS to manage complex workflows and multiple runs.

^^^^^^^^^^^^^^^^^^^^^^
Creating New Runspaces
^^^^^^^^^^^^^^^^^^^^^^

Creating new runspaces from a simulation configuration file is simple by invoking the following from the command line:

    ``ips.py --create-runspace --simulation=simulation_conf.ips``

This will create a new directory using the simulation contained in the ``SIM_NAME`` variable. Within this directory, a subdirectory named ``work`` will be created that will house the working directories for all of the components used in the simulation. In addition, a directory named ``simulation_setup`` will be created that houses the component scripts for the simulation.

All configuration files, the ``platform.conf`` and ``simulation_conf.ips`` files, will be copied into the simulation base directory. Additionally, any data files that are needed by the simulation's components will be staged into the working directories for their respective components.

^^^^^^^^^
Run-setup
^^^^^^^^^

After a runspace has been created, additional tasks may need to be performed in the parsing of input files, interpolating of data, or trasforming of datapoints between coordinate spaces. These steps may be time or computation intensive, and consist of all of the data preparation that is necessary before a run can begin. As such, these steps should be relegated to a run-setup stage of a workflow.

Run-setup steps that need to be performed should be contained in the ``init()`` implementation of simulation driver component. To perform only the run-setup step, invoke the following on the command line:

    ``ips.py --run-setup --simulation=simulation_conf.ips``

This will invoke only the ``driver.init()`` method, which will perform only run-setup related tasks.

^^^^^^^
Running
^^^^^^^

Once run-setup has been completed, a run can be performed by invoking the following on the command line:

    ``ips.py --run --simulation=simulation_conf.ips``

This will invoke the ``step()`` and ``finalize()`` methods on the driver component, which will execute the run. 

^^^^^^^
Cloning
^^^^^^^

All of the inputs necessary to duplicate a run are stored in a container file named with the ``SIM_NAME`` variable. Given a container file, a clone of a run can be created by invoking the following on the command line:

    ``ips.py --clone=simulation.ctz --sim_name=new_simulation``

This creates a new simulation_conf.ips with the name passed in the ``sim_name`` command line option.The Framework will open the container file, copy the ``simulation_conf.ips`` file contained within, replace the ``SIM_NAME`` value in this file with the passed in ``sim_name`` value, and unzip the required files into the new directory.

^^^^^^^^^^^^^
Multiple Runs
^^^^^^^^^^^^^

From a single command line invocation, multiple runs can be performed by utilizing comma-separated values. In the following example:

    ``ips.py --create-runspace --simulation=a.ips,b.ips``

Two simulation files, ``a.ips`` and ``b.ips``, are used to create runspaces for two new simulations.

The Framework can also allow the handling of multiple clones, as in the following example:

    ``ips.py --clone=a.ctz,b.ctz --sim_name=x,y``

Two container files ``a.ctz`` and ``b.ctz`` are used to clone two simulations ``a`` and ``b``, and the clones are renamed ``x`` and ``y`` respectively.



