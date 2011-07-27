#! /usr/bin/env python
"""
   # local version
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
      D. Schnack, and J. Wright, *Simulation of Wave Interations with MHD*, 
      in Rick Stevens, editor, SciDAC 2008, 14-17 July 2008, Washington, USA, 
      volume 125 of Journal of Physics: Conference Series, page 012039, 
      Institute of Physics, 2008.
    - Wael R. Elwasif, David E. Bernholdt, Lee A. Berry, and Don B. 
      Batchelor, *Component Framework for Coupled Integrated Fusion 
      Plasma Simulation*, in HPC-GECO/CompFrame 2007, 21-22 October, 
      Montreal, Quebec, Canada, 2007. 

      
   :Authors: Wael R. Elwasif, Samantha Foley, Aniruddha G. Shet
   :Organization: Center for Simulation of RF Wave Interactions 
                  with Magnetohydrodynamics (`CSWIM <http://www.cswim.org>`_)

"""
import sys
import multiprocessing
from messages import Message, ServiceRequestMessage, \
                    ServiceResponseMessage, MethodInvokeMessage
from configurationManager import ConfigurationManager
from taskManager import TaskManager
from resourceManager import ResourceManager
from dataManager import DataManager
from componentRegistry import ComponentRegistry
import socket
import getopt
from componentRegistry import ComponentID
from ipsExceptions import BlockedMessageException
from eventService import EventService
from cca_es_spec import initialize_event_service
import logging
from ips_es_spec import eventManager
import os
import ipsTiming
import time
#from ipsTiming import *

def make_timers():
    """
    Create TAU timers to be used to profile simulation execution.
    """
    mypid = str(os.getpid())
    timer_funcs = ['__init__', '_dispatch_service_request', '_invoke_framework_comps',
                   'run', '_send_monitor_event','terminate_sim']
    timer_dict = {}
    for i in range(len(timer_funcs)):
        timer_dict[timer_funcs[i]] = ipsTiming.create_timer("fwk", timer_funcs[i], mypid)
    return timer_dict

TIMERS = make_timers()
""" A dictionary mapping method names in the `Framework`_ object to tau
    timers.
"""

class Framework(object):
    #@ipsTiming.TauWrap(TIMERS['__init__'])
    def __init__(self, do_create_runspace = False, do_run_setup = False, 
            do_run = False, config_file_list, log_file, simulation_filename, 
            platform_file_name, debug=False, ftb=False, verbose_debug = False, 
            cmd_nodes = 0, cmd_ppn = 0):
        """
        Create an IPS Framework Instance to coordinate the execution of IPS simulations
        
        The Framework performs the following main tasks:
        
          * Initialize the different IPS managers that perform the bulk of the framework functionality
          * Manage communication queues, and route service requests from simulation 
            components to appropriate managers.
          * Provide logging services to IPS managers.
          * Perfrom shutdown procedure on exit     

        Args:
            config_file_list: [list] A list of simulation configuration files to be used
                in the simulaion. Each simulation configuration file must have the following
                parameters
           
                * *SIM_ROOT*    The root directory for the simulation
                * *SIM_NAME*    A name that identifies the simulation
                * *LOG_FILE*    The name of a log file that is used to capture logging and error information
                                 for this simulation.
                        
                *SIM_ROOT*, *SIM_NAME*, and *LOG_FILE* must be unique across simulations.
            log_file: [file] A file object where Framework logging messages are placed. 
            platform_file_name: [string] The name of the paltform configuration file used in the simulation.
            debug: [boolean] A flag indicating whether framework debugging messages are enabled (default = False)
            ftb: [boolean]  A flag indicating whether integration with the Fault tolerance Backplane 
                Protocaol (FTB) is enabled (default = False)
            verbose_debug: [boolean] A flag adding more verbose framework debugging (default = False)

        """
        #self.timers = make_timers()
        #start(self.timers['__init__'])
        self.ftb = ftb
        self.log_file = log_file
        self.in_queue = multiprocessing.Queue(0)
        self.comp_registry = ComponentRegistry()
        self.component_id = ComponentID(self.__class__.__name__, 'FRAMEWORK')
        self.port_map = {}
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
             ConfigurationManager(self, config_file_list, platform_file_name)
        self.resource_manager = ResourceManager(self)
        self.data_manager = DataManager(self)
        self.task_manager = TaskManager(self)
        ipsTiming.instrument_object_with_tau('Fwk', self, exclude = ['__init__'])
        ipsTiming.instrument_object_with_tau('ConfigMgr', self.config_manager)
        ipsTiming.instrument_object_with_tau('ResourceMgr', self.resource_manager)
        ipsTiming.instrument_object_with_tau('EventMgr', self.event_manager)
        ipsTiming.instrument_object_with_tau('DataMgr', self.data_manager)
        # define a Handler which writes INFO messages or higher to the sys.stderr
        logger = logging.getLogger("FRAMEWORK")
        self.log_level = logging.WARNING
        if debug :
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
        # add the handler to the root logger
        try:
            # each manager should create their own event manager if they want to send and receive events
            self.config_manager.initialize(self.data_manager,
                                           self.resource_manager,
                                           self.task_manager,
                                           self.ftb)
            self.task_manager.initialize(self.data_manager,
                                         self.resource_manager,
                                         self.config_manager,
                                         self.ftb)
            self.resource_manager.initialize(self.data_manager,
                                             self.task_manager,
                                             self.config_manager,
                                             self.ftb,
                                             cmd_nodes,
                                             cmd_ppn)
        except Exception, e:
            self.exception("Problem initializing managers")
            self.terminate_sim(status=Message.FAILURE)
            #stop(self.timers['__init__'])
            raise 
        self.blocked_messages = []
        #stop(self.timers['__init__'])

    def get_inq(self):
        """
        Return handle to the Framework's input queue object (`multiprocessing.Queue <http://docs.python.org/library/multiprocessing.html>`_)
        """
        return self.in_queue

    def register_service_handler(self, service_list, handler):
        """
        Register a call back method to handle a list of framework service 
        invocations.
        
          * *handler*: a Python callable object that takes a :py:obj:`messages.ServiceRequestMessage`.
          * *service_list*: a list of service names to call *handler* when invoked by components.  The service name must match the *target_method* parameter in ``messages.ServiceRequestMessage``. 
           
        """
        for svc in service_list:
            self.service_handler[svc] = handler

    def _dispatch_service_request(self, msg):
        """
        Find and execute handler that corresponds to the *target_method* of 
        *msg*, a :py:obj:`messages.ServiceRequestMessage` object.  If handler 
        not found an exception is raised.  The return value from the handler 
        method is conveyed to the caller along the appropriate queue in a 
        :py:obj:`messages.ServiceResponseMessage`.  All exceptions are passed 
        on to the caller, except for the 
        :py:obj:`ipsException.BlockedMessageException`, which causes the 
        message to be blocked until the request can be satisfied.
        """
        method_name = msg.target_method
        comp_id = msg.sender_id
        self.debug('Framework dispatching method: %s from %s', method_name, str(comp_id))
        try:
            handler = self.service_handler[method_name]
        except KeyError, e:
            self.exception("Unsupported method : %s", method_name)
            response_msg = ServiceResponseMessage(self.component_id,
                                 comp_id,
                                 msg.message_id,
                                 Message.FAILURE, 
                                 Exception("Unsupported method : %s" % (method_name)))
        else:
            try:
                ret_val = handler(msg)
            except BlockedMessageException, e:
                if self.verbose_debug:
                    self.debug('Blocked message : %s', e.__str__())
                self.blocked_messages.append(msg)
                #stop(self.timers['_dispatch_service_request'])
                return
            except Exception, e:
                self.exception('Exception handling service message: %s - %s', str(msg.__dict__), str(e))
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
                                                         'svc_response_q' )
        response_q.put(response_msg)
        return

    def log(self, *args):
        """
        Wrapper for :py:meth:`Framework.info`.
        """
        return self.info(*args)

    def debug(self, *args):
        """
        Produce **debugging** message in simulation log file.  Raise exception for bad formatting.  
        """
        
        try:
            if (len(args) > 1):
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.debug(msg)
        except:
            self.error('Bad format in call to fwk.debug() ' + str(args))

    def info(self, *args):
        """
        Produce **informational** message in simulation log file.  Raise exception for bad formatting.  
        """
        try:
            if (len(args) > 1):
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.info(msg)
        except:
            self.error('Bad format in call to fwk.info() ' + str(args))
            
    def warning(self, *args):
        """
        Produce **warning** message in simulation log file.  Raise exception for bad formatting.  
        """
        try:
            if (len(args) > 1):
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.warning(msg)
        except:
            self.error('Bad format in call to fwk.warning() ' + str(args))

    def error(self, *args):
        """
        Produce **error** message in simulation log file.  Raise exception for bad formatting.  
        """
        try:
            if (len(args) > 1):
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.error(msg)
        except:
            self.error('Bad format in call to fwk.error() ' + str(args))

    def exception(self, *args):
        """
        Produce **exception** message in simulation log file.  Raise exception for bad formatting.  
        """
        try:
            if (len(args) > 1):
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.exception(msg)
        except:
            self.error('Bad format in call to fwk.exception() ' + str(args))

    def critical(self, *args):
        """
        Produce **critical** message in simulation log file.  Raise exception for bad formatting.  
        """
        try:
            self.logger.critical(*args)
        except:
            print 'error in Framework.critical', args
            raise

    #@ipsTiming.TauWrap(TIMERS['_invoke_framework_comps'])
    def _invoke_framework_comps(self, fwk_comps, method_name):
        """
        Invoke *method_name* on components in *fwk_comps* (list of component 
        ids).  Typically, this is 
        all framework-attached components (portal bridge and FTB bridge).  The 
        calling method blocks until all invocations terminate. No arguments 
        are passed to the invoked methods.
        """

        #start(self.timers['_invoke_framework_comps'])
        outstanding_fwk_calls = []
        for comp_id in fwk_comps:
            msg = ServiceRequestMessage(self.component_id,
                                        self.component_id, comp_id,
                                       'init_call', method_name, 0)
            self.debug('Framework sending message %s ', msg.__dict__)
            call_id = self.task_manager.init_call(msg, manage_return=False)
            outstanding_fwk_calls.append(call_id)

        self.blocked_messages = []
        while (len(outstanding_fwk_calls) > 0):
            self.debug("Framework waiting for message")
            msg = self.in_queue.get()
            self.debug("Framework received Message : %s", str(msg.__dict__))
            msg_list = [msg] + self.blocked_messages
            self.blocked_messages = []
            for msg in msg_list:
                self.debug('Framework processing message %s ', msg.message_id)
                if (msg.__class__.__name__ == 'ServiceRequestMessage'):
                    self._dispatch_service_request(msg)
                    continue
                elif (msg.__class__.__name__ == 'MethodResultMessage'):
                    self.debug('Received Result for call %s' %
                                   (msg.call_id))
                    if msg.call_id not in outstanding_fwk_calls:
                        self.task_manager.return_call(msg)
                    else:
                        if (msg.status == Message.FAILURE):
                            self.terminate_sim(status=Message.FAILURE)
                            #stop(self.timers['_invoke_framework_comps'])
                            raise msg.args[0]
                        outstanding_fwk_calls.remove(msg.call_id)
                else:
                    self.error('Framework received unexpected message : %s',
                               str(msg.__dict__))
        #stop(self.timers['invoke_framework_comps'])

    #@ipsTiming.TauWrap(TIMERS['run'])
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
        :py:meth:`Framework.terminate_sim` is called to trigger normal 
        termination of all component processes.
        """
        #start(self.timers['run'])
        try:
            fwk_comps = self.config_manager.get_framework_components()
            sim_comps = self.config_manager.get_component_map()
            outstanding_sim_calls = {}
        except Exception, e:
            self.exception('encountered exception during fwk.run() initialization')
            self.terminate_sim(status=Message.FAILURE)
            #stop(self.timers['run'])
            return False

        # All Framework components must finish their init() calls before 
        # proceeding to
        # execute step(), and invoke simulation components

        self._invoke_framework_comps(fwk_comps, 'init')

        try:
            # Each Framework Component is treated as a stand-alone simulation
            # generate the queues of invocation messages for each framework component
            for comp_id in fwk_comps:
                msg_list = []
                for method in ['step', 'finalize']:
                    req_msg = ServiceRequestMessage(self.component_id,
                                                    self.component_id, comp_id,
                                                    'init_call', method, 0)
                    msg_list.append(req_msg)
                outstanding_sim_calls[comp_id] = msg_list
            # generate a queue of invocation messages for each simulation
            #   - the list will look like: [init_comp.init(),
            #                               init_comp.step(),
            #                               init_comp.finalize(),
            #                               driver.init(),
            #                               driver.step(),
            #                               driver.finalize()]
            # these messages will be sent on a FIFO basis, thus running the init components,
            # then the corresponding drivers.
            for sim_name, comp_list in sim_comps.items():
                msg_list = []
                self._send_monitor_event(sim_name, 'IPS_START', 'Starting IPS Simulation')
                comment = 'Nodes = %d   PPN = %d' % \
                            (self.resource_manager.num_nodes, self.resource_manager.ppn)
                self._send_monitor_event(sim_name, 'IPS_RESOURCE_ALLOC', comment)
                if self.ftb:
                    self._send_ftb_event('IPS_START')
                for comp_id in comp_list:
                    for method in ['init', 'step', 'finalize']:
                        req_msg = ServiceRequestMessage(self.component_id,
                                                        self.component_id, comp_id,
                                                        'init_call', method, 0)
                        msg_list.append(req_msg)
                outstanding_sim_calls[sim_name] = msg_list
        except Exception, e:
            self.exception('encountered exception during fwk.run() genration of call messages')
            self.terminate_sim(status=Message.FAILURE)
            #stop(self.timers['run'])
            return False

        call_id_list = []
        call_queue_map = {}
        # send off first round of invocations...
        try:
            for sim_name, msg_list in outstanding_sim_calls.items():
                msg = msg_list.pop(0)
                self.debug('Framework sending message %s ', msg.__dict__)
                call_id = self.task_manager.init_call(msg, manage_return=False)
                call_queue_map[call_id] = msg_list
                call_id_list.append(call_id)
        except Exception, e:
            self.exception('encountered exception during fwk.run() sending first round of invocations (init of inits and fwk comps)')
            self.terminate_sim(status=Message.FAILURE)
            #stop(self.timers['run'])
            return False

        while (len(call_id_list) > 0):
            if (self.verbose_debug):
                self.debug("Framework waiting for message")
            # get new messages
            try:
                msg = self.in_queue.get()
            except:
                continue
            if (self.verbose_debug):
                self.debug("Framework received Message : %s", str(msg.__dict__))
            
            # add blocked messages to message list for reprocessing
            msg_list = [msg] + self.blocked_messages
            self.blocked_messages = []
            # process new and blocked messages
            for msg in msg_list:
                if (self.verbose_debug):
                    self.debug('Framework processing message %s ', msg.message_id)
                if (msg.__class__.__name__ == 'ServiceRequestMessage'):
                    try:
                        self._dispatch_service_request(msg)
                    except Exception:
                        self.exception('Error dispatching service request message.')
                        self.terminate_sim(status=Message.FAILURE)
                        #stop(self.timers['run'])
                        return False
                    continue
                elif (msg.__class__.__name__ == 'MethodResultMessage'):
                    if msg.call_id not in call_id_list:
                        self.task_manager.return_call(msg)
                        continue
                    # Message is a result from a framework invocation
                    call_id_list.remove(msg.call_id)
                    sim_msg_list = call_queue_map[msg.call_id]
                    del call_queue_map[msg.call_id]
                    if (msg.status == Message.FAILURE):
                        self.error('received a failure message from component %s : %s',
                                   msg.sender_id, str(msg.args))
                        # No need to process remaining messages for this simulation
                        sim_msg_list = []
                        comment = 'Simulation Execution Error'
                        ok = False
                        # self.terminate_sim(status=Message.FAILURE)
                        # return False
                    else:
                        comment = 'Simulation Ended'
                        ok = True
                    try:
                        next_call_msg =  sim_msg_list.pop(0)
                        call_id = self.task_manager.init_call(next_call_msg,
                                                              manage_return=False)
                        call_id_list.append(call_id)
                        call_queue_map[call_id] = sim_msg_list
                    except IndexError:
                        sim_name = msg.sender_id.get_sim_name()
                        if sim_name in sim_comps.keys():
                            self._send_monitor_event(sim_name, 'IPS_END',
                                                    comment, ok)
                            if self.ftb:
                                self._send_ftb_event('IPS_END')
        self.terminate_sim(Message.SUCCESS)
        self.event_service._print_stats()
        #stop(self.timers['run'])
        #dumpAll()
        return True

    #@ipsTiming.TauWrap(TIMERS['_send_monitor_event'])
    def _send_monitor_event(self, sim_name = '', eventType='', comment = '', ok = 'True'):
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
        #start(self.timers['_send_monitor_event'])
        self.debug('_send_monitor_event(%s - %s)',sim_name,  eventType)
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
        if (eventType == 'IPS_START'):
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
        elif (eventType == 'IPS_END'):
            portal_data['state'] = 'Completed'
            portal_data['stopat'] = time.strftime('%Y-%m-%d|%H:%M:%S%Z',
                                                   time.localtime())

        event_body = {}
        event_body['sim_name'] = sim_name
        event_body['sim_root'] = get_config(sim_name, 'SIM_ROOT')
        event_body['portal_data'] = portal_data

        self.debug('Publishing %s', str(event_body))
        self.event_manager.publish(topic_name, 'IPS_SIM', event_body)
        #stop(self.timers['_send_monitor_event'])
        return

    def _send_ftb_event(self, eventType=''):
        """
        Publish an event of type *eventType* to topic *_IPS_FTB*.
        """
        self.debug('_send_ftb_event(%s)',  eventType)
        ftb_data = {}
        ftb_data['eventtype'] = eventType
        topic_name = '_IPS_FTB'
        self.event_manager.publish(topic_name, 'IPS_SIM', ftb_data)
        return

    #@ipsTiming.TauWrap(TIMERS['terminate_sim'])
    def terminate_sim(self, status= Message.SUCCESS):
        """
        Terminate all active component instances by invoking the ``terminate`` 
        method on each one.
        """
        #start(self.timers['terminate_sim'])
        sim_names = self.config_manager.get_sim_names()
        for sim in sim_names:
            comp_ids = self.comp_registry.get_component_ids(sim)
            for id in comp_ids:
                try:
                    invocation_q = self.comp_registry.getComponentArtifact(id,
                                                                           'invocation_q')
                    call_id = self.task_manager.get_call_id()
                    msg = MethodInvokeMessage(self.component_id, id, call_id,
                                              'terminate', status)
                    self.debug('Sending terminate message to %s', str(id))
                    invocation_q.put(msg)
                except Exception, e:
                    self.exception('exception encountered while terminating comp %s', id)
                    print e
        time.sleep(1)
        try:
            self.config_manager.terminate(status)
        except Exception, e:
            self.exception('exception encountered while cleaning up config_manager')
        #sys.exit(status)
        #stop(self.timers['terminate_sim'])


def printUsageMessage():
    """
    Print message on how to run the IPS.
    """
    # with files
    print 'Usage: ips [--create-runspace]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'
    print '       ips [--run-setup]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'
    print '       ips [--run]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]'

def main(argv=None):
    """
    Check and parse args, create and run the framework.
    """
#    print "hello from main"

    cfgFile_list = []
    platform_filename = ''
    simulation_filename = ''
    log_file = sys.stdout
    # parse command line arguments
    if argv is None:
        argv = sys.argv
        first_arg = 1
    else:
        first_arg = 0

    try:
        opts, args = getopt.gnu_getopt(argv[first_arg:], '',
                                       ["create-runspace", "run-setup", "run", 
                                        "simulation=", "platform=", "log=", 
                                        "nodes=", "ppn=",
                                        "debug", "verbose", "ftb"])
    except getopt.error, msg:
        print 'Invalid command line arguments', msg
        printUsageMessage()
        return 1
    debug = False
    ftb = False
    verbose_debug = False
    cmd_nodes = 0
    cmd_ppn = 0
    # flags for the action to perform
    do_create_runspace = False
    do_run_setup = False
    do_run = False
    # flag for platform file present
    platform_file_specified = False
    simulation_file_specified = False
    for arg, value in opts:
        if (arg == '--create-runspace'):
            # create the runspace
            # cfgFile_list.append(value)
            do_create_runspace = True
        elif (arg == '--run-setup'):
            # setup for run
            # cfgFile_list.append(value)
            do_run_setup = True
        elif (arg == '--run');
            # run
            # cfgFile_list.append(value)
            do_run = True
        elif (arg == '--log'):
            log_file_name = value
            try:
                log_file = open(os.path.abspath(log_file_name), 'w')
            except Exception, e:
                print 'Error writing to log file ' , log_file_name
                print str(e)
                raise
        elif (arg == '--simulation'):
            simulation_filename = value
            cfgFile_list.append(value)
            simulation_file_specified = True
        elif (arg == '--platform'):
            platform_filename = value
            platform_file_specified = True
        elif (arg == '--nodes'):
            cmd_nodes = int(value)
        elif (arg == '--ppn'):
            cmd_ppn = int(value)
        elif (arg == '--debug'):
            debug = True
        elif (arg == '--ftb'):
            ftb = True
        elif (arg == '--verbose'):
            verbose_debug = True

    # if a --platform file was not specified, use default
    # if the default doesn't exist, raise an exception
    if (not platform_file_specified):
        platform_filename = 'platform.conf'
        try:
            platform_file = open(os.path.abspath(platform_filename), 'r')
        except Exception, e:
            print 'Error reading from platform.conf file '
            print str(e)
            raise

    if (not simulation_file_specified):
        simulation_filename = 'core-edge.conf'
        try:
            simulation_file = open(os.path.abspath(simulation_filename), 'r')
        except Exception, e:
            print 'Error reading from core-edge.conf file '
            print str(e)
            raise

    # if no config files were specified, print usage and exit
    if (len(cfgFile_list) == 0):
        printUsageMessage()
        return 1
    # if no options were specified
    elif ((do_create_runspace + do_run_setup + do_run) == 0):
        # do everything
        do_create_runspace = True
        do_run_setup = True
        do_run = True

    #print "got cmd ln args"
    #print 'cfgFile_list: ', cfgFile_list
    # create framework with config file
    try:
        fwk = Framework(do_create_runspace, do_run_setup, do_run, cfgFile_list, 
                log_file, simulation_filename, platform_filename, debug, ftb, 
                verbose_debug, cmd_nodes, cmd_ppn)
        fwk.run()
        ipsTiming.dumpAll('framework')
    except :
        raise 
    return 0

# ----- end main -----

if __name__ == "__main__":
    print "Starting IPS"
    sys.stdout.flush()
    #args = '--config=sim.conf --config=sim2.conf --platform=jaguar.conf'
    #args = '--config=basic_concurrent1.conf --platform=odin.conf'
    #argv = args.split(' ')
    #argv = sys.argv
    sys.exit(main())

#if __name__ == "__main__":
#    fwk = Framework()
#    fwk.run()
