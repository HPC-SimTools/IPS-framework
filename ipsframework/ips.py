#! /usr/bin/env python3
# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
   The Integrated Plasma Simulator (IPS) Framework. This framework enables
   loose, file-based coupling of certain class of nuclear fusion simulation
   codes.

   For further design information see

    - Wael Elwasif, David E. Bernholdt, Aniruddha G. Shet, Samantha S. Foley,
      Randall Bramley, Donald B. Batchelor, and Lee A. Berry, *The Design and
      Implementation of the SWIM Integrated Plasma Simulator*, in The 18th
      Euromirco International Conference on Parallel, Distributed and
      Network - Based Computing (PDP 2010), 2010.
    - Samantha S. Foley, Wael R. Elwasif, David E. Bernholdt, Aniruddha G.
      Shet, and Randall Bramley, *Extending the Concept of Component
      Interfaces: Experience with the Integrated Plasma Simulator*, in
      Component - Based High - Performance Computing (CBHPC) 2009, 2009,
      (extended abstract).
    - D Batchelor, G Alba, E D'Azevedo, G Bateman, DE Bernholdt, L Berry,
      P Bonoli, R Bramley, J Breslau, M Chance, J Chen, M Choi, W Elwasif,
      S Foley, G Fu, R Harvey, E Jaeger, S Jardin, T Jenkins, D Keyes, S
      Klasky, S Kruger, L Ku, V Lynch, D McCune, J Ramos, D Schissel, D
      Schnack, and J Wright, *Advances in Simulation of Wave Interactions with
      Extended MHD Phenomena*, in Horst Simon, editor, SciDAC 2009, 14-18 June
      2009, San Diego, California, USA, volume 180 of Journal of Physics:
      Conference Series, page 012054, Institute of Physics, 2009, 6pp.
    - Samantha S. Foley, Wael R. Elwasif, Aniruddha G. Shet, David E.
      Bernholdt, and Randall Bramley, *Incorporating Concurrent Component
      Execution in Loosely Coupled Integrated Fusion Plasma Simulation*, in
      Component-Based High-Performance Computing (CBHPC) 2008, 2008,
      (extended abstract).
    - D. Batchelor, C. Alba, G. Bateman, D. Bernholdt, L. Berry, P. Bonoli,
      R. Bramley, J. Breslau, M. Chance, J. Chen, M. Choi, W. Elwasif,
      G. Fu, R. Harvey, E. Jaeger, S. Jardin, T. Jenkins, D. Keyes,
      S. Klasky, S. Kruger, L. Ku, V. Lynch, D. McCune, J. Ramos, D. Schissel,
      D. Schnack, and J. Wright, *Simulation of Wave Interactions with MHD*,
      in Rick Stevens, editor, SciDAC 2008, 14-17 July 2008, Washington, USA,
      volume 125 of Journal of Physics: Conference Series, page 012039,
      Institute of Physics, 2008.
    - Wael R. Elwasif, David E. Bernholdt, Lee A. Berry, and Don B.
      Batchelor, *Component Framework for Coupled Integrated Fusion
      Plasma Simulation*, in HPC-GECO/CompFrame 2007, 21-22 October,
      Montreal, Quebec, Canada, 2007.


   :Authors: Wael R. Elwasif, Samantha Foley, Aniruddha G. Shet
   :Organization: Center for Simulation of RF Wave Interactions
                  with Magnetohydrodynamics

"""
import sys
import argparse
import multiprocessing
import inspect
import socket
import logging
import os
import time
from ipsframework import platformspec
from ipsframework.messages import Message, ServiceRequestMessage, \
    ServiceResponseMessage, MethodInvokeMessage
from ipsframework.configurationManager import ConfigurationManager
from ipsframework.taskManager import TaskManager
from ipsframework.resourceManager import ResourceManager
from ipsframework.dataManager import DataManager
from ipsframework.componentRegistry import ComponentRegistry, ComponentID
from ipsframework.ipsExceptions import BlockedMessageException
from ipsframework.eventService import EventService
from ipsframework.cca_es_spec import initialize_event_service
from ipsframework.ips_es_spec import eventManager
from ipsframework._version import get_versions

if sys.version[0] != '3':  # noqa: E402
    print("IPS can is only compatible with Python 3.5 or higher")
    sys.exit(1)


class Framework:
    """Create an IPS Framework Instance to coordinate the execution of IPS simulations

    The Framework performs the following main tasks:

      * Initialize the different IPS managers that perform the bulk of the framework functionality
      * Manage communication queues, and route service requests from simulation
        components to appropriate managers.
      * Provide logging services to IPS managers.
      * Perform shutdown procedure on exit

    :param config_file_list: A list of simulation configuration files to be used
            in the simulaion. Each simulation configuration file must have the following
            parameters

            * *SIM_ROOT*    The root directory for the simulation
            * *SIM_NAME*    A name that identifies the simulation
            * *LOG_FILE*    The name of a log file that is used to capture logging and error information for this simulation.

            *SIM_ROOT*, *SIM_NAME*, and *LOG_FILE* must be unique across simulations.
    :type config_file_list: list

    :param log_file_name: A file name where Framework logging messages are placed.
    :type log_file_name: str

    :param platform_file_name: The name of the platform
            configuration file used in the simulation.  If not
            specified it will try to find the one installed in the
            share directory.
    :type platform_file_name: str

    :param debug: A flag indicating whether framework debugging messages are enabled (default = False)
    :type debug: bool

    :param verbose_debug: A flag adding more verbose framework debugging (default = False)
    :type verbose_debug: bool

    :param cmd_nodes: Computer nodes (default = 0)
    :type cmd_nodes: int

    :param cmd_ppn: Computer processor per nodes (default = 0)
    :type cmd_ppn: int
    """
    def __init__(self, config_file_list, log_file_name, platform_file_name=None,
                 debug=False, verbose_debug=False, cmd_nodes=0, cmd_ppn=0):
        # added compset_list for list of components to load config files for
        # command line option
        print("Starting IPS", get_versions()['version'])
        os.environ['IPS_INITIAL_CWD'] = os.getcwd()

        self.log_file_name = log_file_name
        if log_file_name == 'sys.stdout':
            self.log_file = sys.stdout
        else:
            self.log_file = open(os.path.abspath(log_file_name), 'w')
        # the multiprocessing queue
        self.in_queue = multiprocessing.Queue(0)
        # registry of components for calling
        self.comp_registry = ComponentRegistry()
        # reference to this class's component ID
        self.component_id = ComponentID(self.__class__.__name__, 'FRAMEWORK')
        # map of ports
        self.port_map = {}

        current_dir = inspect.getfile(inspect.currentframe())
        (self.platform_file_name, self.ipsShareDir) = \
            platformspec.get_share_and_platform(platform_file_name,
                                                current_dir)

        # config file list
        self.config_file_list = config_file_list

        # host is set in the configuration manager, not needed here???????
        self.host = socket.gethostname()
        self.logger = None
        self.service_handler = {}
        self.cur_time = time.time()
        self.start_time = self.cur_time
        self.event_service = EventService(self)
        initialize_event_service(self.event_service)
        self.event_manager = eventManager(self)
        self.config_manager = \
            ConfigurationManager(self, self.config_file_list, self.platform_file_name)
        self.resource_manager = ResourceManager(self)
        self.data_manager = DataManager(self)
        self.task_manager = TaskManager(self)
        # define a Handler which writes INFO messages or higher to the sys.stderr
        logger = logging.getLogger("FRAMEWORK")
        self.log_level = logging.WARNING
        if debug:
            self.log_level = logging.DEBUG
        # create handler and set level to debug
        logger.setLevel(self.log_level)
        ch = logging.StreamHandler(self.log_file)
        ch.setLevel(self.log_level)
        # create formatter
        formatter = logging.Formatter("%(asctime)s %(name)-15s %(levelname)-8s %(message)s")
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        logger.addHandler(ch)
        self.logger = logger
        self.verbose_debug = verbose_debug
        self.outstanding_calls_list = []
        self.call_queue_map = {}

        # add the handler to the root logger
        try:
            # each manager should create their own event manager if they
            # want to send and receive events
            self.config_manager.initialize(self.data_manager,
                                           self.resource_manager,
                                           self.task_manager)
            self.task_manager.initialize(self.data_manager,
                                         self.resource_manager,
                                         self.config_manager)
            self.resource_manager.initialize(self.data_manager,
                                             self.task_manager,
                                             self.config_manager,
                                             cmd_nodes,
                                             cmd_ppn)
        except Exception:
            self.exception("Problem initializing managers")
            self.terminate_all_sims(status=Message.FAILURE)
            raise
        self.blocked_messages = []
        # SIMYAN: determine the sim_root for the Framework to use later
        fwk_comps = self.config_manager.get_framework_components()
        main_fwk_comp = self.comp_registry.getEntry(fwk_comps[0])
        self.sim_root = os.path.abspath(main_fwk_comp.services.get_config_param('SIM_ROOT'))

    def get_inq(self):
        """
        :return: handle to the Framework's input queue object
        :rtype: :class:`multiprocessing.Queue`
        """
        return self.in_queue

    def register_service_handler(self, service_list, handler):
        """
        Register a call back method to handle a list of framework service
        invocations.

        :param service_list: a list of service names to call *handler* when invoked by components.
             The service name must match the *target_method* parameter in :class:`messages.ServiceRequestMessage`.

        :param handler: a Python callable object that takes a :class:`messages.ServiceRequestMessage`.

        """
        for svc in service_list:
            self.service_handler[svc] = handler

    def _dispatch_service_request(self, msg):
        """
        Find and execute handler that corresponds to the *target_method* of
        *msg*, a :class:`messages.ServiceRequestMessage` object.  If handler
        not found an exception is raised.  The return value from the handler
        method is conveyed to the caller along the appropriate queue in a
        :class:`messages.ServiceResponseMessage`.  All exceptions are passed
        on to the caller, except for the
        :class:`ipsExceptions.BlockedMessageException`, which causes the
        message to be blocked until the request can be satisfied.
        """
        method_name = msg.target_method
        comp_id = msg.sender_id
        self.debug('Framework dispatching method: %s from %s', method_name, str(comp_id))
        try:
            handler = self.service_handler[method_name]
        except KeyError:
            self.exception("Unsupported method : %s", method_name)
            response_msg = ServiceResponseMessage(self.component_id,
                                                  comp_id,
                                                  msg.message_id,
                                                  Message.FAILURE,
                                                  Exception("Unsupported method : %s" % (method_name)))
        else:
            try:
                ret_val = handler(msg)
            except BlockedMessageException as e:
                if self.verbose_debug:
                    self.debug('Blocked message : %s', e.__str__())
                self.blocked_messages.append(msg)
                return
            except Exception as e:
                # self.exception('Exception handling service message: %s - %s', str(msg.__dict__), str(e))
                response_msg = ServiceResponseMessage(self.component_id,
                                                      comp_id,
                                                      msg.message_id,
                                                      Message.FAILURE, e)
            else:
                response_msg = ServiceResponseMessage(self.component_id,
                                                      comp_id,
                                                      msg.message_id,
                                                      Message.SUCCESS, ret_val)

        response_q = self.comp_registry.getComponentArtifact(comp_id,
                                                             'svc_response_q')
        response_q.put(response_msg)

    def log(self, msg, *args):
        """
        Wrapper for :meth:`Framework.info`.
        """
        return self.info(msg, *args)

    def debug(self, msg, *args):
        """
        Produce **debugging** message in simulation log file. See :func:`logging.debug` for usage.
        """
        self.logger.debug(msg, *args)

    def info(self, msg, *args):
        """
        Produce **informational** message in simulation log file. See :func:`logging.info` for usage.
        """
        self.logger.info(msg, *args)

    def warning(self, msg, *args):
        """
        Produce **warning** message in simulation log file. See :func:`logging.warning` for usage.
        """
        self.logger.warning(msg, *args)

    def error(self, msg, *args):
        """
        Produce **error** message in simulation log file. See :func:`logging.error` for usage.
        """
        self.logger.error(msg, *args)

    def exception(self, msg, *args):
        """
        Produce **exception** message in simulation log file. See :func:`logging.exception` for usage.
        """
        self.logger.exception(msg, *args, exc_info=False)

    def critical(self, msg, *args):
        """
        Produce **critical** message in simulation log file. See :func:`logging.critical` for usage.
        """
        self.logger.critical(msg, *args)

    def _invoke_framework_comps(self, fwk_comps, method_name):
        """
        Invoke *method_name* on components in *fwk_comps* (list of component
        ids).  Typically, this is
        all framework-attached components (portal bridge).  The
        calling method blocks until all invocations terminate. No arguments
        are passed to the invoked methods.
        """

        outstanding_fwk_calls = []
        for comp_id in fwk_comps:
            msg = ServiceRequestMessage(self.component_id,
                                        self.component_id, comp_id,
                                        'init_call', method_name, 0)
            self.debug('Framework sending message %s ', msg.__dict__)
            call_id = self.task_manager.init_call(msg, manage_return=False)
            outstanding_fwk_calls.append(call_id)

        self.blocked_messages = []
        while len(outstanding_fwk_calls) > 0:
            self.debug("Framework waiting for message")
            msg = self.in_queue.get()
            self.debug("Framework received Message : %s", str(msg.__dict__))
            msg_list = [msg] + self.blocked_messages
            self.blocked_messages = []
            for msg in msg_list:
                self.debug('Framework processing message %s ', msg.message_id)
                if msg.__class__.__name__ == 'ServiceRequestMessage':
                    self._dispatch_service_request(msg)
                    continue
                elif msg.__class__.__name__ == 'MethodResultMessage':
                    self.debug('Received Result for call %s' %
                               (msg.call_id))
                    if msg.call_id not in outstanding_fwk_calls:
                        self.task_manager.return_call(msg)
                    else:
                        if msg.status == Message.FAILURE:
                            self.terminate_all_sims(status=Message.FAILURE)
                            raise msg.args[0]
                        outstanding_fwk_calls.remove(msg.call_id)
                else:
                    self.error('Framework received unexpected message : %s',
                               str(msg.__dict__))

    def run(self):
        """
        Run the communication outer loop of the framework.

        This method implements the core communication and message dispatch
        functionality of the framework. The main phases of execution for the
        framework are:

            1. Invoke the ``init`` method on all framework-attached components,
               blocking pending method call termination.
            2. Generate method invocation messages for the remaining public
               method in the framework-centric components (i.e. ``step`` and
               ``finalize``).
            3. Generate a queue of method invocation messages for all public
               framework accessible components in the simulations being run.
               framework-accessible components are made up of the **Init**
               component (if is exists), and the **Driver** component. The
               generated messages invoke the public methods ``init``,
               ``step``, and ``finalize``.
            4. Dispatch method invocations  for each framework-centric
               component and physics simulation in order.

        Exceptions that propagate to this method from the managed simulations
        causes the framework to abort any pending method invocation for the
        source simulation.
        Exceptions from framework-centeric component aborts further
        invocations to that component.

        When all method invocations have been dispatched (or aborted),
        :meth:`configurationManager.ConfigurationManager.terminate_sim` is called to trigger normal
        termination of all component processes.

        :return: Success status
        :rtype: bool
        """
        try:
            fwk_comps = self.config_manager.get_framework_components()
            sim_comps = self.config_manager.get_component_map()
            outstanding_sim_calls = {}
        except Exception:
            self.exception('encountered exception during fwk.run() initialization')
            self.terminate_all_sims(status=Message.FAILURE)
            return False

        # SIMYAN: get the runspaceInit_component and invoke its init() method
        # this creates the base directory and container file for the simulation
        # and copies the conf files into both and change directory to base dir
        main_fwk_comp = self.comp_registry.getEntry(fwk_comps[0])
        self.sim_root = os.path.abspath(main_fwk_comp.services.get_config_param('SIM_ROOT'))
        self._invoke_framework_comps(fwk_comps, 'init')

        try:
            # Each Framework Component is treated as a stand-alone simulation
            # generate the queues of invocation messages for each framework component
            for comp_id in fwk_comps:
                msg_list = []
                for method in ['step', 'finalize']:
                    req_msg = ServiceRequestMessage(self.component_id, self.component_id,
                                                    comp_id, 'init_call', method, 0)
                    msg_list.append(req_msg)

                outstanding_sim_calls[str(comp_id)] = msg_list

            # generate a queue of invocation messages for each simulation
            #   - list will look like: [init_comp.init(), init_comp.step(), init_comp.finalize(),
            #                           driver.init(), driver.step(), driver.finalize()]
            # these messages will be sent on a FIFO basis, thus running the init components,
            # then the corresponding drivers.
            for sim_name, comp_list in list(sim_comps.items()):
                msg_list = []
                self._send_monitor_event(sim_name, 'IPS_START', 'Starting IPS Simulation')
                self._send_dynamic_sim_event(sim_name=sim_name, event_type='IPS_START')
                comment = 'Nodes = %d   PPN = %d' % \
                          (self.resource_manager.num_nodes, self.resource_manager.ppn)
                self._send_monitor_event(sim_name, 'IPS_RESOURCE_ALLOC', comment)
                # SIMYAN: ordered list of methods to call
                methods = ['init', 'step', 'finalize']

                # SIMYAN: add each method call to the msg_list
                for comp_id in comp_list:
                    for method in methods:
                        req_msg = ServiceRequestMessage(self.component_id,
                                                        self.component_id,
                                                        comp_id,
                                                        'init_call', method, 0)
                        msg_list.append(req_msg)
                    # SIMYAN: add the msg_list to the outstanding sim calls
                    if msg_list:
                        outstanding_sim_calls[sim_name] = msg_list

        except Exception:
            self.exception('encountered exception during fwk.run() generation of call messages')
            self.terminate_all_sims(status=Message.FAILURE)
            return False

        # send off first round of invocations...
        try:
            for sim_name, msg_list in list(outstanding_sim_calls.items()):
                msg = msg_list.pop(0)
                self.debug('Framework sending message %s ', msg.__dict__)
                call_id = self.task_manager.init_call(msg, manage_return=False)
                self.call_queue_map[call_id] = msg_list
                self.outstanding_calls_list.append(call_id)
        except Exception:
            self.exception('encountered exception during fwk.run() sending first round of invocations (init of inits and fwk comps)')
            self.terminate_all_sims(status=Message.FAILURE)
            raise

        while len(self.outstanding_calls_list) > 0:
            if self.verbose_debug:
                self.debug("Framework waiting for message")
            # get new messages
            try:
                msg = self.in_queue.get()
            except Exception:
                continue
            if self.verbose_debug:
                self.debug("Framework received Message : %s", str(msg.__dict__))

            # add blocked messages to message list for reprocessing
            msg_list = [msg] + self.blocked_messages
            self.blocked_messages = []
            # process new and blocked messages
            for msg in msg_list:
                if self.verbose_debug:
                    self.debug('Framework processing message %s ', msg.message_id)

                sim_name = msg.sender_id.get_sim_name()
                if msg.__class__.__name__ == 'ServiceRequestMessage':
                    try:
                        self._dispatch_service_request(msg)
                    except Exception:
                        self.exception('Error dispatching service request message.')
                        self.terminate_all_sims(status=Message.FAILURE)
                        return False
                    continue
                elif msg.__class__.__name__ == 'MethodResultMessage':
                    if msg.call_id not in self.outstanding_calls_list:
                        self.task_manager.return_call(msg)
                        continue
                    # Message is a result from a framework invocation
                    self.outstanding_calls_list.remove(msg.call_id)
                    sim_msg_list = self.call_queue_map[msg.call_id]
                    del self.call_queue_map[msg.call_id]
                    if msg.status == Message.FAILURE:
                        self.error('received a failure message from component %s : %s',
                                   msg.sender_id, str(msg.args))
                        # No need to process remaining messages for this simulation
                        sim_msg_list = []
                        comment = 'Simulation Execution Error'
                        ok = False
                        # self.terminate_sim(status=Message.FAILURE)
                        # return False
                        self.send_terminate_msg(sim_name, Message.FAILURE)
                    else:
                        comment = 'Simulation Ended'
                        ok = True
                    try:
                        next_call_msg = sim_msg_list.pop(0)
                        call_id = self.task_manager.init_call(next_call_msg,
                                                              manage_return=False)
                        self.outstanding_calls_list.append(call_id)
                        self.call_queue_map[call_id] = sim_msg_list
                    except IndexError:
                        sim_comps = self.config_manager.get_component_map()  # Get any new dynamic simulations
                        if sim_name in list(sim_comps.keys()):
                            self._send_monitor_event(sim_name, 'IPS_END',
                                                     comment, ok)
                            self._send_dynamic_sim_event(sim_name, 'IPS_END', ok)
                            self.send_terminate_msg(sim_name, Message.SUCCESS)
                            self.config_manager.terminate_sim(sim_name)

        self.terminate_all_sims(Message.SUCCESS)
        self.event_service._print_stats()
        return True

    def _send_monitor_event(self, sim_name='', eventType='', comment='', ok='True'):
        """
        Publish a portal monitor event to the *_IPS_MONITOR* event topic.
        Event topics that start with an underscore are reserved for use by the
        IPS Framework and services.

          * *sim_name*: The name of the simulation to which this even belongs.
          * *eventType*: The type of the event.
          * *comment*: A string containing comment that describes the event.
          * *ok*: A string containing the values 'True' or 'False', based on
            whether the event indicates normal simulation execution, or an
            error condition.
        """
        if self.verbose_debug:
            self.debug('_send_monitor_event(%s - %s)', sim_name, eventType)
        portal_data = {}
        portal_data['code'] = 'Framework'
        # eventData['portal_runid'] = self.portalRunId
        portal_data['eventtype'] = eventType
        portal_data['ok'] = ok
        portal_data['comment'] = comment
        portal_data['walltime'] = '%.2f' % (time.time() - self.start_time)
        topic_name = '_IPS_MONITOR'
        # portal_data['phystimestamp'] = self.timeStamp
        get_config = self.config_manager.get_config_parameter
        if eventType == 'IPS_START':
            portal_data['state'] = 'Running'
            portal_data['host'] = get_config(sim_name, 'HOST')
            try:
                portal_data['outputprefix'] = get_config(sim_name, 'OUTPUT_PREFIX')
            except KeyError:
                pass
            try:
                portal_data['simname'] = sim_name
            except KeyError:
                pass
            try:
                portal_data['tag'] = get_config(sim_name, 'TAG')
            except KeyError:
                pass
            try:
                portal_data['user'] = get_config(sim_name, 'USER')
            except KeyError:
                pass
            try:
                portal_data['rcomment'] = get_config(sim_name, 'SIMULATION_DESCRIPTION')
            except KeyError:
                try:
                    portal_data['rcomment'] = get_config(sim_name, 'RUN_COMMENT')
                except KeyError:
                    portal_data['rcomment'] = 'SWIM simulation run'
            try:
                portal_data['tokamak'] = get_config(sim_name, 'TOKAMAK_ID')
            except KeyError:
                pass
            try:
                portal_data['shotno'] = get_config(sim_name, 'SHOT_NUMBER')
            except KeyError:
                pass
            try:
                portal_data['sim_runid'] = get_config(sim_name, 'RUN_ID')
            except KeyError:
                pass
            portal_data['startat'] = time.strftime('%Y-%m-%d|%H:%M:%S%Z',
                                                   time.localtime(self.start_time))
            portal_data['ips_version'] = get_versions()['version']
        elif eventType == 'IPS_END':
            portal_data['state'] = 'Completed'
            portal_data['stopat'] = time.strftime('%Y-%m-%d|%H:%M:%S%Z',
                                                  time.localtime())

        event_body = {}
        event_body['sim_name'] = sim_name
        event_body['sim_root'] = get_config(sim_name, 'SIM_ROOT')
        event_body['portal_data'] = portal_data

        if self.verbose_debug:
            self.debug('Publishing %s', str(event_body))
        self.event_manager.publish(topic_name, 'IPS_SIM', event_body)

    def _send_dynamic_sim_event(self, sim_name='', event_type='', ok=True):
        self.debug('_send_dynamic_sim_event(%s:%s)', event_type, sim_name)
        event_data = {}
        event_data['eventtype'] = event_type
        event_data['SIM_NAME'] = sim_name
        event_data['ok'] = ok
        topic_name = '_IPS_DYNAMIC_SIMULATION'
        self.debug('Publishing %s', str(event_data))
        self.event_manager.publish(topic_name, 'IPS_DYNAMIC_SIM', event_data)

    def send_terminate_msg(self, sim_name, status=Message.SUCCESS):
        """This method remotely invokes the method
        :meth:`component.Component.terminate` on all componnets in the
        IPS simulation ``sim_name``.

        :param sim_name: The simulation name from which all the components are terminated
        :type sim_name: str

        :param status: message status, defaults to :obj:`messages.Message.SUCCESS`
        :type status: :obj:`messages.Message.SUCCESS`, :obj:`messages.Message.FAILURE`

        """
        comp_ids = self.comp_registry.get_component_ids(sim_name)
        for comp_id in comp_ids:
            try:
                invocation_q = self.comp_registry.getComponentArtifact(comp_id,
                                                                       'invocation_q')
                call_id = self.task_manager.get_call_id()
                msg = MethodInvokeMessage(self.component_id, comp_id, call_id,
                                          'terminate', status)
                self.debug('Sending terminate message to %s', str(comp_id))
                invocation_q.put(msg)
            except Exception as e:
                self.exception('exception encountered while terminating comp %s', comp_id)
                print(e)

    def terminate_all_sims(self, status=Message.SUCCESS):
        """Terminate all active component instances.

        This method remotely invokes the method
        :meth:`component.Component.terminate` on all componnets in the
        IPS simulation.

        :param status: message status, defaults to :obj:`messages.Message.SUCCESS`
        :type status: :obj:`messages.Message.SUCCESS`, :obj:`messages.Message.FAILURE`

        """
        sim_names = self.config_manager.get_sim_names()
        for sim in sim_names:
            self.send_terminate_msg(sim, status)
        time.sleep(1)
        try:
            self.config_manager.terminate(status)
        except Exception:
            self.exception('exception encountered while cleaning up config_manager')
        # sys.exit(status)


def main(argv=None):
    """
    Check and parse args, create and run the framework.
    """
    sys.stdout.flush()

    platform_default = os.environ.get("IPS_PLATFORM_FILE")
    if platform_default:
        print("IPS using platform file :", platform_default)

    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version="%(prog)s " + get_versions()['version'])
    parser.add_argument('--simulation', '-i', '--config', '-j',
                        required=True,
                        help='IPS simulation/config file')
    parser.add_argument('--platform', '-p', dest='platform_filename', default=platform_default,
                        required=not platform_default,
                        help='IPS platform configuration file')
    parser.add_argument('--debug', '-d', default=False, action='store_true',
                        help='Turn on debugging')
    parser.add_argument('--verbose', '-v', dest='verbose_debug', default=False, action='store_true',
                        help='Run IPS verbosely')
    parser.add_argument('--log', '-l', dest='log_file', default='sys.stdout',
                        help='IPS Log file')
    parser.add_argument('--nodes', '-n', dest='cmd_nodes', default='0',
                        type=int, help='Computer nodes')
    parser.add_argument('--ppn', '-o', dest='cmd_ppn', default='0',
                        type=int, help='Computer processor per nodes')

    options = parser.parse_args()

    cfgFile_list = options.simulation.split(',')

    try:
        fwk = Framework(cfgFile_list, options.log_file, options.platform_filename,
                        options.debug, options.verbose_debug,
                        options.cmd_nodes, options.cmd_ppn)
        fwk.run()
    except Exception:
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
