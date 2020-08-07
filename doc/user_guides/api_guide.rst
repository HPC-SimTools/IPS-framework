Developing against the Framework Application Programming Interface
==================================================================

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

.. automethod:: ipsframework.services.ServicesProxy.stage_plasma_state
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.update_plasma_state
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.merge_current_plasma_state
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

The event service interface is used to implement the web portal connection, as well as for components to communicate asynchronously.  See the :doc:`Advanced Features <advanced_parallelism>` documentation for details on how to use this interface for component communication.

.. automethod:: ipsframework.services.ServicesProxy.publish
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.subscribe
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.unsubscribe
   :noindex:

.. automethod:: ipsframework.services.ServicesProxy.process_events
   :noindex:
