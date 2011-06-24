==============
How To Use RUS
==============

This document contains information on how to run RUS alone and using the experiment suite generators and visualizers.

------------
What is RUS?
------------

RUS is a Python script that simulates the execution of tasks in the IPS.  It can produce output related to how the IPS spends its time and resources over the course of a run through simulation.

-----------
Running RUS
-----------

^^^^^^^^^^^^^^^^^
Required Software
^^^^^^^^^^^^^^^^^

* Python (2.6, 2.5 should work)
* ConfigObj (this is actually included in the directory, so you should be ok)
* Matplotlib (for analysis and viz utilities)

^^^^^^
Input
^^^^^^

(All times are in seconds)

;;;;;;;;;;;;
Config File
;;;;;;;;;;;;

The *configuration file* describes the simulation execution characteristics that are to be modeled.

The first section just names the simulation and provides a text description::

    simulation = ant
    description = "aorsa, nubeam, tsc"

For each simulation specified in the previous section, that simulation is described.  The simulation description can be done in two ways: *old-style* and *phases*.  The *old-style* specification lists the components and number of steps in the "General Information Section," while the *phases* method lists the phases that are included in the simulation.  An *old-style* simulation will have one specification of the components behavior and their relationships to each other, whereas a *phases* specification may have different components and execution characteristics in each phase.  It is a way to express periods of time in a IPS simulation where different parts of the physics may interact in different ways, thus requiring more or less compute time or resources.

General Information Section (old-style)::

    [ant]
    name = ANT_wo   # name of the simulation (for human readability)
    components = aorsa, nubeam, tsc # component list
    nsteps = 1000

-----------------------

Simulation overheads are described in the "Overheads Section."  Currently, only ``startup`` and ``shutdown`` are used. ::

    # Simulation overheads
    [[startup]]
      name = startup
      runtime = 15
    [[shutdown]]
      name = shutdown
      runtime = 3

-----------------------

RUS can be used to experiment with different fault tolerance capabilities and responses to determine when each is most applicable.  This section of the configuration file specifies the actions a simulation or component can take.

 * ``ft_strategy``:

   * none: as soon as the first failure causes a *fault* [#fault]_, the simulation dies.
   * sim_cr: simulation level checkpoint and restart [#restart]_ is enabled.  See below for specifying the checkpoint mode and interval.
   * task_relaunch: when a task fails, it is relaunched [#relaunch]_ as specified below.
   * restart: the simulation is restarted from the beginning (losing any work done).

 * ``retry limit``: number of times a single task instance can be retried in a row.
 * ``restart``, ``resubmit``, ``launch_delay`` sections: specify the amount of time each activity consumes.  The purpose is to model the time taken by these overhead activities.
 * ``checkpoint`` section:

   * ckpt_on: if ``True``, checkpoints are recorded, otherwise, no checkpoints are taken and a restart will revert to the beginning, if called upon.
   * ckpt_mode: determines the method by which the next checkpoint is scheduled.
     
      * phys_regular: checkpoints are taken at regular intervals based on *physics* timespecified in ``ckpt_interval``.
      * wall_regular: checkpoints are taken at regular intervals based on *wall clock* time specified in ``ckpt_interval``.
      * phys_explicit: checkpoints are taken at specified times listed in ``ckpt_values``.
      * wall_explicit: checkpoints are taken at specified times listed in ``ckpt_values``.

   * runtime: same as other sections.

::

      # FT section
      ft_strategy = none
      retry_limit = 3
      [[restart]]
        name = restart
	runtime = 20
      [[resubmit]]
        name = resubmit
        runtime = 15
      [[launch_delay]]
        name = launch_delay
        runtime = 60
      [[checkpoint]]
        ckpt_on = False
        ckpt_mode = phys_regular
        ckpt_interval = 50
        runtime = 20
        name = ckpt

.. [#fault] When the simulation would be interrupted due to a (node) failure.  It is possible for an unoccupied node in the allocation to fail, thus not affecting the simulation until there are not enough nodes to run the components.
.. [#restart] Restart the simulation from the last checkpoint or the beginning of time.  Note that this is at the *step* granularity.
.. [#relaunch] Reexecution of the component.

-----------------------

Lastly, each of the components are described.  The ``depends_on`` entry is a list of components that must execute before the component being describes runs.  (Be sure that at least one component **does not** have any dependencies, so it can run first.)  The resource needs are then specified in terms of *processes*.  Currently, only ``num_proc`` is used.  The time it takes for the component to execute is specified by its average time ``runtime`` and a standard deviation to describe the amount of time any given run of the component will take.  Currently, no overheads within an execution of a component are taken into account.  It is assumed that the runtime value accounts for any and all pre- and post-execution activities of the component.

Component Section (old-style)::

      [[nubeam]]
        name = nubeam
        description = ""
        depends_on = aorsa
	# resource needs
        num_proc = 512
        mem_pproc = 1
        disk_pproc = 1
        # runtime specification
        runtime = 1020
        stddev =  300
	# overheads
        start_up = 5
        clean_up = 10


;;;;;;;;;;;;;
Resource File
;;;;;;;;;;;;;

The resource file describes the allocation in which we are simulating the execution of the IPS.  Currently, ``machine_name``, ``nodes``, and ``ppn`` are the only required fields.  ``mem_pernode`` and ``disk_pernode`` are placeholders for future work.

RUS may model faults following an exponential or weibull (with shape parameter) distribution, and a mean time between failure (mtbf), measured in seconds.

::

    machine_name = unicorn  # not really important for RUS, 
    # meant to   match the IPS inputs
    nodes =  268
    ppn =  4
    mem_pernode = 0    # not used at this time, can be omitted
    disk_pernode = 0   # not used at this time, can be omitted
    # Optional FT parameters
    distribution = weibull  # exponential is another dist.
    shape = 0.7             # only used for weibull dist.
    mtbf = 126144000        # 4 years of time in seconds


^^^^^^^^^^^
How to Run
^^^^^^^^^^^
After you have set up your configuration file and resource file, you are now ready to run RUS.  The script has two mandatory commandline arguments (the configuration and resource file) as well as a number of flags the control the behavior of the simulation and the output that is produced. ::

  /ips/trunk/framework/utils/RUS > python rus.py 
  				   -c config_files/sample_conf    \
  	  			   -r resource_files/sample_res   \
				   [-l -s -v -d -f -b] 
      -c, --config       : file containing component information
      -r, --resource     : file containing resource info
      -l, --log          : log file name, default is 
      	  		   log.<config file name>_<num procs>.readable
      -s, --seed         : seed for random number generator, otherwise 
      	  		   current time in seconds is used
      -v, --produce_viz  : resource utilization over the course of the 
      	  		   simulation is produced
      -d, --debug        : debugging output is produced
      -f, --failures_on  : failures as specified in the resource file
                           are produced
      -b, --resubmit_on  : resubmission [#resubmit]_ of the simulation
      	  		   in a new batch allocation is turned on

.. [#resubmission] A resubmission is triggered when there are not enough nodes to make progress in the simulation(s).  A new allocation is obtained and each simulation is restarted from the last checkpoint, if present.  Currently, there is a hard limit of 5 resubmissions, set in ``simulation.py``.

^^^^^^^^^^^
Output
^^^^^^^^^^^
There are multiple places you can find output from RUS, on standard out, in the log file, and possibly as a visualization.

* Standard out:
  
  For ease of scripting, the only output that is produced when      
  debugging is not turned on is a series of numbers in the following
  order:
  
    * status: 'Succeeded' if the simulation was able to complete,    
      otherwise, 'Failed.'
    * seed: random number seed used for this run. 
    * total time: total time charged by the system (in other words,
      spent in an allocation).
    * allocation size: number of nodes requested.
    * CPU hrs charged: the number of *hours* charged for this run.                                                           
    * CPU hrs used: the number of *hours* used for this run.  
    * work time: amount of time spent doing work.
    * rework time: amount of time spend redoing work.
    * ckpt time: amount of time spent taking check points.
    * restart time: amount of time spent loading data from a
      checkpoint.
    * launch delay time: amount of time spent delaying task
      relaunches.
    * resubmit time: amount of time spent setting up the framework and simulation in a new batch allocation.
    * overhead time: amount of time spent doing other overhead activities (for instance, simulation startup and shutdown).
    * # ckpts: number of checkpoints taken
    * # node failures: number of node failures that occurred over the
      course of the simulation.
    * # faults: number of interrupts experienced by the application.
    * # relaunch: number of times any task was relaunched.
    * # restart: number of times the simulation was rolled back and
      restarted from a checkpoint
    * # resubmit: number of times the framework ran out of nodes and
      started again in a new batch allocation from the beginning or a
      checkpoint.

* Log file:

  The log file details the resource allocation and release over the
  course of the simulation.  A line is written whenever a component,
  simulation or overhead activity is started or completed, showing 
  the current time, the simulation, the component name, the resource
  utilization, and a message about what happened::

    0 fwk --- start_sim 0.0 %   0 268 # starting simulation
    0 ANT_wo_0 --- start_task 0.0 %   0 268 # started overhead phase startup
    15 ANT_wo_0 --- finish_task 0.0 %   0 268 # finished overhead startup
    15 ANT_wo_0 --- state_change 0.0 %   0 268 # work
    15 ANT_wo_0 startup end_step 0.0 %   0 268 # ending simulation startup
    15 ANT_wo_0 --- phase_change 0.0 %   0 268 # none
    15 ANT_wo_0 startup start_step 0.0 %   0 268 # starting new step 1
    15 ANT_wo_0 nubeam waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    15 ANT_wo_0 tsc waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    15 ANT_wo_0 aorsa start_task 95.5223880597 %   256 268 # started running on 1024 processes on 256 nodes
    1043.81184343 ANT_wo_0 aorsa finish_task 0.0 %   0 268 # finished running
    1043.81184343 ANT_wo_0 tsc waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    1043.81184343 ANT_wo_0 nubeam start_task 47.7611940299 %   128 268 # started running on 512 processes on 128 nodes
    1935.63053396 ANT_wo_0 nubeam finish_task 0.0 %   0 268 # finished running
    1935.63053396 ANT_wo_0 tsc start_task 0.373134328358 %   1 268 # started running on 1 processes on 1 nodes
    2052.02665865 ANT_wo_0 tsc finish_task 0.0 %   0 268 # finished running
    2052.02665865 ANT_wo_0 --- end_step 0.0 %   0 268 # ending step 1
    2052.02665865 ANT_wo_0 nubeam waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    2052.02665865 ANT_wo_0 tsc waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    2052.02665865 ANT_wo_0 aorsa start_task 95.5223880597 %   256 268 # started running on 1024 processes on 256 nodes
    3073.96129245 ANT_wo_0 aorsa finish_task 0.0 %   0 268 # finished running
    3073.96129245 ANT_wo_0 tsc waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    3073.96129245 ANT_wo_0 nubeam start_task 47.7611940299 %   128 268 # started running on 512 processes on 128 nodes
    4873.71805068 ANT_wo_0 nubeam finish_task 0.0 %   0 268 # finished running
    4873.71805068 ANT_wo_0 tsc start_task 0.373134328358 %   1 268 # started running on 1 processes on 1 nodes
    5035.0416603 ANT_wo_0 tsc finish_task 0.0 %   0 268 # finished running
    5035.0416603 ANT_wo_0 --- end_step 0.0 %   0 268 # ending step 2
    5035.0416603 ANT_wo_0 nubeam waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    5035.0416603 ANT_wo_0 tsc waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    5035.0416603 ANT_wo_0 aorsa start_task 95.5223880597 %   256 268 # started running on 1024 processes on 256 nodes
    6049.11839764 ANT_wo_0 aorsa finish_task 0.0 %   0 268 # finished running
    6049.11839764 ANT_wo_0 tsc waiting_on_parents 0.0 %   0 268 # waiting on (at least one) parents
    6049.11839764 ANT_wo_0 nubeam start_task 47.7611940299 %   128 268 # started running on 512 processes on 128 nodes
    7328.15438282 ANT_wo_0 nubeam finish_task 0.0 %   0 268 # finished running
    7328.15438282 ANT_wo_0 tsc start_task 0.373134328358 %   1 268 # started running on 1 processes on 1 nodes

  This is all  
  prefaced with information about the run, including the name of the
  config files and resource file. ::

    % The following data is associated with the run executed at 13_Jan_2011-21.38.22
    % On host agentp.ornl.gov with configuration files:
    % config_files/ANT_restart
    % resource_files/res_n268_p4_w7
    % =================================================================




* Visualization:
  
  If the visualization flag is turned on, three resource usage plots will be generated.  The example images were generated from a RUS run using ``phases_ft`` in a 60 node, 4 processes per node allocation with an exponential distribution and an MTBF of 1261440 seconds.

    * **usage_graph1-<timestamp>.pdf** the red line shows the percent resource (node) usage over time (in seconds).

      .. image:: ../usage_graph1-20.38.13.pdf
      
    *  **usage_graph2-<timestamp>.pdf** the red line shows the resource (node) usage (as a percentage) over time (in seconds), the cyan circles show nodes failures, and the black X's show application faults.

       .. image:: ../usage_graph2-20.38.13.pdf

    *  **usage_graph3-<timestamp>.pdf** is the same as above, but with the actual node counts and a green line indicating the size of the allocation.

       .. image:: ../usage_graph3-20.38.13.pdf


--------------------
The Experimentinator
--------------------

The experimentinator is a script to run a series of RUS simulations exploring the effects of varying the number of simultaneous simulations and batch allocations.

^^^^^^^^^^
Input
^^^^^^^^^^

^^^^^^^^^^
How to Run
^^^^^^^^^^

Once you are comfortable running some standalone RUS runs, and would like to see what happens when you vary the interleaving and/or allocation size, you can use the experimentinator to do so. ::

  /ips/trunk/framework/utils/RUS > python experimentinator.py
                                   -f config_files/sample_conf    \
				   -m 
                                   [-i, -t, -n, -j, -p]
      -i, --interleave   : number of simulations that execute at the
                           same time (default = 4)
      -p, --ppn          : processes per node (default = 4)
      -t, --trials       : number of times to run each experiment
      	  		   (default = 1)
      -n, --name         : name of experiment to help with
          		   identification (default = '')
      -m, --minnodes     : minimum number of nodes needed to run the
                       	   sim(s) 
      -f, --cfile        : path to config file to simulate
      -j, --nodeinterval : number of nodes between allocation sizes to
      	  		   simulate (default = 4)

The configuration file will be the same as the one for RUS, and the experimentinator will generate the resource files for each batch allocation that make sense (from ``minnnodes`` to ``interleave`` * ``minnodes`` by steps of ``nodeinterval``).  Currently, the experimentinator does not generate resource files with a fault injection model, but does handle simulations with phases.


^^^^^^^^^^
Output
^^^^^^^^^^

* Standard out:
* Dump and Summary Files:
* Visualization:

---------------------------------------------------
Running a suite of experiments with ``run_exps.py``
---------------------------------------------------

This script was developed to generate and manage the execution of several RUS runs to examine the effectiveness and cost of different fault tolerance strategies.



^^^^^^^^^^^
Input
^^^^^^^^^^^

This script uses files that contain multiple configuration files and resource files that are to be combined in various ways to form an experiment.

^^^^^^^^^^^
How to Run
^^^^^^^^^^^

For this script, the configuration file list and resource file list are required to construct all possible combinations of files, while the number of trials and name ar optional.  It is important to note that there will be variation in how many and when faults will be generated, as well as the normal variation in execution time of the components in the simulations.

::

	> python run_exps.py -c cfiles -r rfiles -t 20 -n blah

    	-t, --trials      : number of times to run each unique combination of config and resource files (default = 1)
    	-n, --name        : name of experiment to help with identification of dump and log files (default = 'hhh')
    	-c, --config_list : path to file containing line separated config file names
    	-r, --res_list    : path to file containing line separated resource file names

For each combination of configuration file and resource file, ``rus.py`` is run with the *failures_on* and *resubmit_on* flags.  Additionally, the value of *name* is passed as the logfile identifier.

^^^^^^^^^^^
Output
^^^^^^^^^^^

* Standard out:
  The output of each RUS run is printed to the screen, but serves no real purpose.  The data is aggregated and printed to a file after all of the runs are executed.

* Dump file:
  Data from the set of runs are written to a file called ``dump_plot_data`` + <timestamp>.  This file contains a header listing the configuration files, resource files and the number of trials performed, followed by a heading describing the data layout.  The columns of numbers are separated by one space and are as folows:

    * success/failure: "Succeeded" if the simulation was successful, "Failed" otherwise.
    * fault tolerance strategy: see `Config File`_ section on fault tolerance options
    * fault model: see `Resource File`_ section
    * total time
    * allocation size (in nodes)
    * work time: time spent doing new work
    * rework time: time spent doing work again
    * checkpoint time: time spend doing checkpointing
    * restart time: time spent doing restart procedures
    * launch delay: time spent waiting to relaunch a task
    * resubmit time: time spent setting up the framework and simulation
    * overhead time: time spent doing other simulation and framework activities
    * number of checkpoints
    * number of node failures
    * number of faults
    * number of task relaunches
    * number of restarts
    * number of resubmits
    * percent work time
    * percent rework time
    * percent checkpoint time
    * percent restart time
    * percent launch delay time
    * percent resubmit time
    * percent overhead time


----------------------------------
Visualizing with ``viz_engine.py``
----------------------------------

This script analyzes and visualizes the data produced by ``run_exps``.

^^^^^^^^^^^
Input
^^^^^^^^^^^

This script uses the dump file from ``run_exps`` to generate plots and other output files.

^^^^^^^^^^^
How to Run
^^^^^^^^^^^

::

  > python viz_engine.py dump_plot_data23.08.31

^^^^^^^^^^^
Output
^^^^^^^^^^^

Four plots are generated:

* Figure 1: ??
* Figure 2: Average Time Spent per FT Policy, breaks down the time spent doing work and the various other activities and groups them according to FT strategy.  
* Figure 3: Average Time to Solution per FT Policy, the red line shows the average amount of time to complete the simulation without overheads, the bars represent the total time it takes to run the simulation to completion.  The bars are grouped by FT strategy.
* Figure 4: Shows a comparison between checkpoint/restart (C/R) and C/R with task relaunch (T/R).  The graphs compare the percentage of trials that are successful and the cost of fault tolerance, versus the checkpoint interval size.

... and one text file.  The text file breaks down the tests in different ways, including by: success, allocation size, strategy, and fault model.