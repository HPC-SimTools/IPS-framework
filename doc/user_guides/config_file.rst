==================================
The Configuration File - Explained
==================================

This section will detail the different sections and fields of the configuration file and how they relate to a simulation.  The configuration file is designed to let the user to easily set data items used by the framework, components, tasks, and the portal from run to run.  There are user specific, platform specific, and component specific entries that need to be modified or verified before running the IPS in the given configuration.  After a short overview of the syntax of the package used by the framework to make sense of the configuration file, a detailed explanation of each line of the configuration file is presented.

-------------------------------
Syntax and the ConfigObj module
-------------------------------

ConfigObj_ is a Python package for reading and writing config files.  The syntax is similar to shell syntax (e.g., use of $ to reference variables), uses square brackets to create named sections and nested subsections, comma-separated lists and comments indicated by a "#".

In the example configuration file below, curly braces (``{}``) are used to clarify references to variables with underscores (``_``).  Any left-hand side value can be used as a variable after it is defined.  Additionally, any platform configuration value can be referenced as a variable in the configuration file as well.

.. _ConfigObj : http://www.voidspace.org.uk/python/configobj.html


----------------------------------
Configuration File - Line by Line
----------------------------------

**Platform Configuration Override Section**
It is possible for the configuration file to override entries in the platform configuration file.  It is rare and users should use caution when overriding these values.  See :doc:`Platform Configuration File - Explained<platform>` for details on these values.

::

#HOST = 
#MPIRUN = 
#NODE_ALLOCATION_MODE = 


**User Data Section**

The following items are specific to the user and should be changed accordingly.  They will help you to identify your runs in the portal (*USER*), and also store the data from your runs in particular web-enabled locations for post-processing (*USER_W3_DIR* on the local machine, *USER_W3_BASEURL* on the portal).  All of the items in this section are optional.

::

  USER_W3_DIR = /project/projectdirs/m876/www/ssfoley
  USER_W3_BASEURL = http://portal.nersc.gov/project/m876/ssfoley
  USER = ssfoley		# Optional, if missing the unix username is used


**Simulation Information Section**
These items describe this configuration and is used for describing and locating its output, information for the portal, and location of the source code of the IPS.

\*\* Mandatory items: *SIM_ROOT*, *SIM_NAME*, *LOG_FILE*

*RUN_ID*, *TOKOMAK_ID*, *SHOT_NUMBER* - identifiers for the simulation that are helpful for SWIM users.  They ore often used to form a hierarchical name for the simulation, identifying related runs.

*OUTPUT_PREFIX* - used to prevent collisions and overwriting of different simulations using the same *SIM_ROOT*.

*SIM_NAME* - used to identify the simulation on the portal, and often to name the output tree.

*LOG_FILE* - name of the log file for this simulation.  The framework log file is specified at the command line.

*LOG_LEVEL* - sets the logging level for the simulation.  If empty, the framework log level is used, which defaults to *WARNING*.  See :ref:`logging-api` for details on the logging capabilities in the IPS.  Possible values: *DEBUG*, *INFO*, *WARNING*, *ERROR*, *EXCEPTION*, *CRITICAL*.

*SIM_ROOT* - location of output tree.  This directory will be created if it does not exist.  If the directory already exists, then data files will be added, possibly overwriting existing data.


::

  RUN_ID = Model_seq             # Identifier for this simulation run
  TOKAMAK_ID = ITER
  SHOT_NUMBER = 1              # Identifier for specific case for this tokamak 
  	      		       # (should be character integer)

  SIM_NAME = ${RUN_ID}_${TOKAMAK_ID}_${SHOT_NUMBER}

  OUTPUT_PREFIX = 
  LOG_FILE = ${RUN_ID}_sim.log 
  LOG_LEVEL = DEBUG             # Default = WARNING

  # Simulation root - path of the simulation directory that will be constructed 
  # by the framework
  SIM_ROOT = /scratch/scratchdirs/ssfoley/seq_example

  # Description of the simulation for the portal
  SIMULATION_DESCRIPTION = sequential model simulation using generic driver.py
  RUN_COMMENT = sequential model simulation using generic driver.py
  TAG = sequential_model			# for grouping related runs


**Simulation Mode**

This section describes the mode in which to run the simulation.  All values are optional.
  
*SIMULATION_MODE* - describes whether the simulation is starting from *init* (*NORMAL*) or restarting from a checkpoint (*RESTART*).  The default is *NORMAL*.  For RESTART, a restart time and directory must be specified.  These values are used by the driver to control how the simulation is initialized.  *RESTART_TIME* must coincide with a checkpoint save
time.  *RESTART_DIRECTORY* may be $SIM_ROOT if there is an 
existing current simulation there, and the new work will be appended, such 
that it looks like a seamless simulation.

*NODE_ALLOCATION_MODE* - sets the default execution mode for tasks in this simulation.  If the value is *EXCLUSIVE*, then tasks are assigned whole nodes.  If the value is *SHARED*, sub-node allocation is used so tasks can shared nodes thus using the allocation more efficiently.  It is the users responsibility to understand how node sharing will impact the performance of their tasks.

::
 
  SIMULATION_MODE = NORMAL   # NORMAL | RESTART
  RESTART_TIME = 12         # time step to restart from
  RESTART_ROOT = ${SIM_ROOT}
  NODE_ALLOCATION_MODE = EXCLUSIVE # SHARED | EXCLUSIVE


**Plasma State Section**

The locations and names of the plasma state files are specified here, along with the directory where the global plasma state files are located in the simulation tree.  It is common to specify groups of plasma state files for use in the component configuration sections.  These files should contain all the shared data values for the simulation so that they can be managed by the driver.

::

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
  PLASMA_STATE_FILES1 = ${CURRENT_STATE} ${PRIOR_STATE}  ${NEXT_STATE} ${CURRENT_EQDSK}
  PLASMA_STATE_FILES2 = ${CURRENT_CQL} ${CURRENT_DQL} ${CURRENT_JSDSK}
  PLASMA_STATE_FILES = ${PLASMA_STATE_FILES1} ${PLASMA_STATE_FILES2}


**Ports Section**

The ports section identifies which ports and their associated implementations that are to be used for this simulation.  The ports section is defined by ``[PORTS]``.  *NAMES* is a list of port names, where each needs to appear as a subsection (e.g., ``[[DRIVER]]``).  Each port definition section must contain the entry *IMPLEMENTATION* whose value is the name of a component definition section.  These are case sensitive names and should be named such that someone familiar the components of this project has an understanding of what is being modeled.  The only mandatory port is *DRIVER*.  It should be named *DRIVER*, but the implementation can be anything, as long as it is defined.  If no *INIT* port is defined, then the framework will produce a warning to that effect.  There may be more port definitions than listed in *NAMES*.

::

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


**Component Configuration Section**

Component definition and configuration is done in this "section."  Each component configuration section is defined as a section (e.g., ``[model_RF_IC]``).  Each entry in the component configuration section is available to the component at runtime using that name (e.g., *self.NPROC*), thus these values can be used to create specific simulation cases using generic components.  Variables defined within a component configuration section are local to that section, but values may be defined in terms of the simulation values defined above (e.g., *PLASMA_STATE_FILES*).

\*\* Mandatory entries: *SCRIPT*, *NAME*, *BIN_PATH*, *INPUT_DIR*

*CLASS* - commonly this is the port name or the first directory name in the path to the component implementation in ``ips/components/``.

*SUB_CLASS* - commonly this is the name of the code or method used to model this port, or the second directory name in the path to the component implementation in ``ips/components/``.

*NAME* - name of the class in the Python script that implements this component.

*NPROC* - number of processes on which to launch tasks.

*BIN_PATH* - path to script and any other helper scripts and binaries.  This is used by the framework and component to find and execute helper scripts and binaries.

*BINARY* - the binary to launch as a task.  Typically, these binaries are found in the 

*PHYS_BIN* or some subdirectory therein.  Otherwise, you can make your own variable and put the directory where the binary is located there.

*INPUT_DIR* - directory where the input files (listed below) are found.  This is used during initialization to copy the input files to the work directory of the component.

*INPUT_FILES* - list of files (relative to *INPUT_DIR*) that need to be copied to the component work directory on initialization. 
*OUTPUT_FILES* - list of output files that are produced that need to be protected and archived on a call to :py:meth:`services.ServicesProxy.stage_output_files`.

*PLASMA_STATE_FILES* - list of plasma state files used and modified by this component.  If not present, then the files specified in the simulation entry *PLASMA_STATE_FILES* is used.

*RESTART_FILES* - list of files that need to be archived as the checkpoint of this component.

*NODE_ALLOCATION_MODE* - sets the default execution mode for tasks in this component.  If the value is *EXCLUSIVE*, then tasks are assigned whole nodes.  If the value is *SHARED*, sub-node allocation is used so tasks can share nodes thus using the allocation more efficiently.  If no value or entry is present, the simulation value for *NODE_ALLOCATION_MODE* is used.  It is the users responsibility to understand how node sharing will impact the performance of their tasks.  This can be overridden using the *whole_nodes* and *whole_sockets* arguments to :py:meth:`services.ServicesProxy.launch_task`.

Additional values that are specific to the component may be added as needed, for example certain data values like *PPN*, paths to and names of other executables used by the component or alternate *NPROC* values are examples.  It is the responsibility of the component writer to make sure users know what values are required by the component and what the valid values are for each.

::
         
  [model_EPA]
      CLASS = epa
      SUB_CLASS = model_epa
      NAME = model_EPA
      NPROC = 1
      BIN_PATH = ${IPS_ROOT}/bin
      INPUT_DIR = ${DATA_TREE_ROOT}/model_epa/ITER/hy040510/t20.0
          INPUT_STATE_FILE = hy040510_002_ps_epa__tsc_4_20.000.cdf
          INPUT_EQDSK_FILE = hy040510_002_ps_epa__tsc_4_20.000.geq 
          INPUT_FILES = model_epa_input.nml ${INPUT_STATE_FILE} ${INPUT_EQDSK_FILE} 
          OUTPUT_FILES = internal_state_data.nml
          PLASMA_STATE_FILES = ${CURRENT_STATE} ${NEXT_STATE} ${CURRENT_EQDSK}
          RESTART_FILES = ${INPUT_FILES} internal_state_data.nml
      SCRIPT = ${BIN_PATH}/model_epa_ps_file_init.py

  [monitor_comp_4]
      CLASS = monitor
      SUB_CLASS = 
      NAME = monitor
      NPROC = 1
      W3_DIR = ${USER_W3_DIR}              # Note this is user specific
      W3_BASEURL = ${USER_W3_BASEURL}      # Note this is user specific
      TEMPLATE_FILE= basic_time_traces.xml 
      BIN_PATH = ${IPS_ROOT}/bin
      INPUT_DIR = ${IPS_ROOT}/components/monitor/monitor_4
      INPUT_FILES = basic_time_traces.xml 
      OUTPUT_FILES = monitor_file.nc
      PLASMA_STATE_FILES = ${CURRENT_STATE}
      RESTART_FILES = ${INPUT_FILES} monitor_restart monitor_file.nc
      SCRIPT = ${BIN_PATH}/monitor_comp.py


**Checkpoint Section**

This section describes when checkpoints should be taken by the simulation.  Drivers should be written such that at the end of each step there is a call to :py:meth:`services.ServicesProxy.checkpoint_components`.  This way the services use the settings in this section to either take a checkpoint or not.

Selectively checkpoint components in *comp_id_list* based on the configuration section *CHECKPOINT*.  If *Force* is ``True``, the checkpoint will be taken even if the conditions for taking the checkpoint are not met.  If *Protect* is ``True``, then the data from the checkpoint is protected from clean up.  *Force* and *Protect* are optional and default to ``False``.

The *CHECKPOINT_MODE* option controls determines if the components checkpoint methods are invoked.  Possible *MODE* options are:

WALLTIME_REGULAR:
    checkpoints are saved upon invocation of the service call           
    ``checkpoint_components()``, when a time interval greater than, or  
    equal to, the value of the configuration parameter                  
    WALLTIME_INTERVAL had passed since the last checkpoint. A           
    checkpoint is assumed to have happened (but not actually stored)    
    when the simulation starts. Calls to ``checkpoint_components()``    
    before WALLTIME_INTERVAL seconds have passed since the last         
    successful checkpoint result in a NOOP.

WALLTIME_EXPLICIT:                                                      
    checkpoints are saved when the simulation wall clock time exceeds 
    one of the (ordered) list of time values (in seconds) specified in 
    the variable WALLTIME_VALUES. Let [t_0, t_1, ..., t_n] be the list 
    of wall clock time values specified in the configuration parameter 
    WALLTIME_VALUES. Then checkpoint(T) = True if T >= t_j, for some j 
    in [0,n] and there is no other time T_1, with T > T_1 >= T_j such   
    that checkpoint(T_1) = True.  If the test fails, the call results   
    in a NOOP.                                                          

PHYSTIME_REGULAR:                                                       
    checkpoints are saved at regularly spaced                           
    "physics time" intervals, specified in the configuration parameter 
    PHYSTIME_INTERVAL. Let PHYSTIME_INTERVAL = PTI, and the physics     
    time stamp argument in the call to checkpoint_components() be       
    pts_i, with i = 0, 1, 2, ... Then checkpoint(pts_i) = True if       
    pts_i >= n PTI , for some n in 1, 2, 3, ... and                     
    pts_i - pts_prev >= PTI, where checkpoint(pts_prev) = True and      
    pts_prev = max (pts_0, pts_1, ..pts_i-1). If the test fails, the    
    call results in a  NOOP.

PHYSTIME_EXPLICIT:                                                      
    checkpoints are saved when the physics time                         
    equals or exceeds one of the (ordered) list of physics time values 
    (in seconds) specified in the variable PHYSTIME_VALUES. Let [pt_0, 
    pt_1, ..., pt_n] be the list of physics time values specified in    
    the configuration parameter PHYSTIME_VALUES. Then                   
    checkpoint(pt) = True if pt >= pt_j, for some j in [0,n] and there 
    is no other physics time pt_k, with pt > pt_k >= pt_j such that     
    checkpoint(pt_k) = True. If the test fails, the call results in a   
    NOOP.                                                               
                                                                                
The configuration parameter NUM_CHECKPOINT controls how many            
checkpoints to keep on disk. Checkpoints are deleted in a FIFO manner, 
based on their creation time. Possible values of NUM_CHECKPOINT are:

   * NUM_CHECKPOINT = n, with n > 0  --> Keep the most recent n checkpoints
   * NUM_CHECKPOINT = 0  --> No checkpoints are made/kept (except when *Force* = ``True``)                                                                
   * NUM_CHECKPOINT < 0 --> Keep ALL checkpoints

Checkpoints are saved in the directory ``${SIM_ROOT}/restart``    

::

  [CHECKPOINT]
     MODE = WALLTIME_REGULAR
     WALLTIME_INTERVAL = 15
     NUM_CHECKPOINT = 2
     PROTECT_FREQUENCY = 5  

**Time Loop Section**

The time loop specifies how time progresses for the simulation in the driver.  It is not required by the framework, but may be required by the driver.  Most simulations use the time loop section to specify the number and frequency of time steps for the simulation as opposed to hard coding it into the driver.  It is a helpful tool to control the runtime of each step and the overall simulation.  It can also be helpful when looking at a small portion of time in the simulation for debugging purposes.

*MODE* - defines the following entries.  If mode is *REGULAR* -- *START*, *FINISH* and *NSTEP* are used to generate a list of times of length *NSTEP* starting at *START* and ending at *FINISH*.  If mode is *EXPLICIT* -- *VALUES* contains the (whitespace separated) list of times that are are to be modeled.

::

  [TIME_LOOP]
      MODE = REGULAR
      START = 0.0
      FINISH = 20.0 
      NSTEP = 5 
