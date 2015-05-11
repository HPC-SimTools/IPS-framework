#! /usr/bin/env python
#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
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
import glob, fnmatch
import os
import socket
import getopt
import time
import logging
import optparse
import multiprocessing
import platform
import shutil
import ipsutil
import zipfile
import inspect
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
import checklist
from configobj import ConfigObj
#from ipsTiming import *

def make_timers():
    """
    Create TAU timers to be used to profile simulation execution.
    """
    mypid = str(os.getpid())
    timer_funcs = ['__init__', '_dispatch_service_request', '_invoke_framework_comps',
                   'run', '_send_monitor_event','terminate_all_sims']
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
    # SIMYAN: added options for creating runspace, run-setup, and running,
    # added compset_list for list of components to load config files for
    def __init__(self, do_create_runspace, do_run_setup, do_run,
            config_file_list, log_file_name, platform_file_name=None,
            compset_list=None, debug=False,
            ftb=False, verbose_debug = False, cmd_nodes = 0, cmd_ppn = 0):
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
            log_file_name: [file] A file name where Framework logging messages are placed.
            platform_file_name: [string] The name of the platform
               configuration file used in the simulation.  If not specified it will try to find the
               one installed in the share directory.
            compset_list: [list] Other path information can be found in the
               component-<component_name>.conf file in the share directory.  You can pass in
               compset_list to use this file.
               These files must contain

                  * *BIN_PATH*   Location of component scripts
                  * *INPUT_DIR*  Location of input files

                If you are using  multiple files, then it is recommended to duplicate these
                variables with a name spacing string to allow for a simulation file to use the
                multiple locations.
                If component list is not specified, then it is assumed that these variables are
                defined in the platform.conf file (backward compatibility).
            debug: [boolean] A flag indicating whether framework debugging messages are enabled (default = False)
            ftb: [boolean]  A flag indicating whether integration with the Fault tolerance Backplane
                Protocol (FTB) is enabled (default = False)
            verbose_debug: [boolean] A flag adding more verbose framework debugging (default = False)

        """
        #self.timers = make_timers()
        #start(self.timers['__init__'])

        # SIMYAN: collect the steps to do in this invocation of the Framework
        self.ips_dosteps={}
        self.ips_dosteps['CREATE_RUNSPACE'] = do_create_runspace # create runspace: init.init()
        self.ips_dosteps['RUN_SETUP']       = do_run_setup    # validate inputs: sim_comps.init()
        self.ips_dosteps['RUN']             = do_run          # Main part of simulation

        # fault tolerance flag
        self.ftb = ftb
        # SIMYAN: set the logging to either file or sys.stdout based on
        # command line option
        self.log_file_name = log_file_name
        if log_file_name == 'sys.stdout':
            self.log_file=sys.stdout
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

        # SIMYAN: Complicated here to allow for a generalization of previous
        # functionality and to enable the automatic finding of the files
        self.compset_list=None

        current_dir = inspect.getfile(inspect.currentframe())
        (self.platform_file_name, self.ipsShareDir) = \
                        platform.get_share_and_platform(platform_file_name,
                                                        current_dir)

        checked_compset_list=[]
        #if not self.ipsShareDir == '':
        if compset_list:
            for cname in compset_list:
                cfile='component-'+cname+'.conf'
                fullcfile=os.path.join(self.ipsShareDir,cfile)
                if os.path.exists(fullcfile):
                    checked_compset_list.append(fullcfile)
            if not len(checked_compset_list):
                #print "Cannot find specified component configuration files."
                #print "  Assuming that variables are defined anyway"
                pass
            else:
                self.compset_list=checked_compset_list
        else:
            if os.path.exists(os.path.join(self.ipsShareDir,'component-generic.conf')):
                checked_compset_list.append(os.path.join(self.ipsShareDir,'component-generic.conf'))
                self.compset_list=checked_compset_list
            else:
                #print "Cannot find any component configuration files."
                #print "  Assuming that variables are defined anyway"
                pass

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
        # SIMYAN: added a few parameters to Configuration Manager for
        # component files
        self.config_manager = \
             ConfigurationManager(self, self.config_file_list,self.platform_file_name, self.compset_list)

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
        self.outstanding_calls_list=[]
        self.call_queue_map = {}

        # add the handler to the root logger
        try:
            # each manager should create their own event manager if they
            # want to send and receive events
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
            self.terminate_all_sims(status=Message.FAILURE)
            #stop(self.timers['__init__'])
            raise
        self.blocked_messages = []
        #stop(self.timers['__init__'])
        # SIMYAN: determine the sim_root for the Framework to use later
        fwk_comps = self.config_manager.get_framework_components()
        main_fwk_comp = self.comp_registry.getEntry(fwk_comps[0])
        self.sim_root = os.path.abspath(main_fwk_comp.services.get_config_param('SIM_ROOT'))

    def get_inq(self):
        """
        Return handle to the Framework's input queue object
         (`multiprocessing.Queue <http://docs.python.org/library/multiprocessing.html>`_)
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
                #self.exception('Exception handling service message: %s - %s', str(msg.__dict__), str(e))
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
                            self.terminate_all_sims(status=Message.FAILURE)
                            #stop(self.timers['_invoke_framework_comps'])
                            raise msg.args[0]
                        outstanding_fwk_calls.remove(msg.call_id)
                else:
                    self.error('Framework received unexpected message : %s',
                               str(msg.__dict__))
        #stop(self.timers['invoke_framework_comps'])

    #@ipsTiming.TauWrap(TIMERS['run'])
    @property
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
            self.terminate_all_sims(status=Message.FAILURE)
            #stop(self.timers['run'])
            return False

        # SIMYAN: required fields for the checklist file
        self.required_fields = set(['CREATE_RUNSPACE', 'RUN_SETUP', 'RUN'])

        # SIMYAN: get the runspaceInit_component and invoke its init() method
        # this creates the base directory and container file for the simulation
        # and copies the conf files into both and change directory to base dir
        self.ips_status={}
        main_fwk_comp = self.comp_registry.getEntry(fwk_comps[0])
        self.sim_root = os.path.abspath(main_fwk_comp.services.get_config_param('SIM_ROOT'))
        self.checklist_file = os.path.join(self.sim_root, 'checklist.conf')
        ### SIMYAN:
        ## Get the status of the simulation
        #
        self.ips_status=checklist.get_status(self.checklist_file)

        if self.ips_dosteps['CREATE_RUNSPACE'] and self.ips_status['CREATE_RUNSPACE']:
            self._invoke_framework_comps(fwk_comps, 'init')
            self.ips_status['CREATE_RUNSPACE'] = True
            self.ips_status['RUN_SETUP'] = False
            self.ips_status['RUN'] = False
        elif self.ips_dosteps['CREATE_RUNSPACE'] and not self.ips_status['CREATE_RUNSPACE']:
            self._invoke_framework_comps(fwk_comps, 'init')
            self.ips_status['CREATE_RUNSPACE'] = True
            self.ips_status['RUN_SETUP'] = False
            self.ips_status['RUN'] = False
        elif not self.ips_dosteps['CREATE_RUNSPACE'] and self.ips_status['CREATE_RUNSPACE']:
            print 'Skipping CREATE_RUNSPACE, option was %s but runspace exists' % \
                    self.ips_dosteps['CREATE_RUNSPACE']
        else:
            print 'Skipping CREATE_RUNSPACE, option was %s and runspace did not exist' % \
                    self.ips_dosteps['CREATE_RUNSPACE']

        try:
            # Each Framework Component is treated as a stand-alone simulation
            # generate the queues of invocation messages for each framework component
            for comp_id in fwk_comps:
                msg_list = []
                for method in ['step', 'finalize']:
                    # SIMYAN: if --create_runspace was specified, add calls
                    # to step() and finalize() for the framework components
                    if self.ips_dosteps['CREATE_RUNSPACE']:
                        req_msg = ServiceRequestMessage(self.component_id, self.component_id,
                                                        comp_id, 'init_call', method, 0)
                        msg_list.append(req_msg)

                # SIMYAN: add those calls to the outstanding call map
                if self.ips_dosteps['CREATE_RUNSPACE']:
                    outstanding_sim_calls[comp_id] = msg_list

            # generate a queue of invocation messages for each simulation
            #   - list will look like: [init_comp.init(), init_comp.step(), init_comp.finalize(),
            #                           driver.init(), driver.step(), driver.finalize()]
            # these messages will be sent on a FIFO basis, thus running the init components,
            # then the corresponding drivers.
            for sim_name, comp_list in sim_comps.items():
                msg_list = []
                self._send_monitor_event(sim_name, 'IPS_START', 'Starting IPS Simulation')
                self._send_dynamic_sim_event(sim_name = sim_name, event_type = 'IPS_START')
                comment = 'Nodes = %d   PPN = %d' % \
                          (self.resource_manager.num_nodes, self.resource_manager.ppn)
                self._send_monitor_event(sim_name, 'IPS_RESOURCE_ALLOC', comment)
                # SIMYAN: ordered list of methods to call
                methods = []
                if self.ftb:
                    self._send_ftb_event('IPS_START')

                if self.ips_dosteps['RUN_SETUP'] and self.ips_status['CREATE_RUNSPACE']:
                    self.ips_status['RUN_SETUP'] = True
                    methods.append('setup')
                elif self.ips_dosteps['RUN_SETUP'] and not self.ips_status['CREATE_RUNSPACE']:
                    self.ips_status['RUN_SETUP'] = False
                    print 'RUN_SETUP was requested, but a runspace does not exist...'
                elif self.ips_status['RUN_SETUP'] and self.ips_status['CREATE_RUNSPACE']:
                    print 'RUN_SETUP already performed by a previous run, continuing...'
                elif self.ips_status['RUN_SETUP'] and not self.ips_status['CREATE_RUNSPACE']:
                    self.ips_status['RUN_SETUP'] = False
                    print 'RUN_SETUP is marked as complete, but a runspace does not exist...'
                else:
                    self.ips_status['RUN'] = False


                if self.ips_dosteps['RUN'] and self.ips_status['RUN_SETUP']:
                    self.ips_status['RUN'] = True
                    methods.append('init')
                    methods.append('step')
                    methods.append('finalize')
                elif self.ips_dosteps['RUN'] and not self.ips_status['RUN_SETUP']:
                    self.ips_status['RUN'] = False
                    print 'RUN was requested, but run setup hasn\'t been performed...'
                elif self.ips_status['RUN'] and self.ips_dosteps['RUN_SETUP']:
                    self.ips_status['RUN'] = False
                    print 'RUN was not requested, but had been performed.'
                elif not self.ips_dosteps['RUN'] and self.ips_status['RUN'] and self.ips_status['RUN_SETUP']:
                    print 'RUN was not requested, but had been performed.'
                else:
                    self.ips_status['RUN'] = False

                errmsg=checklist.update(self.checklist_file,self.ips_status)

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


        except Exception, e:
            self.exception('encountered exception during fwk.run() genration of call messages')
            self.terminate_all_sims(status=Message.FAILURE)
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
                print call_id, msg.__dict__
                self.call_queue_map[call_id] = msg_list
                self.outstanding_calls_list.append(call_id)
        except Exception:
            self.exception('encountered exception during fwk.run() sending first round of invocations (init of inits and fwk comps)')
            self.terminate_all_sims(status=Message.FAILURE)
            raise

        shutdown_time = 1.0E20
        init_shutdown = False
        while len(self.outstanding_calls_list) > 0 and time.time() < shutdown_time:
            if len(self.outstanding_calls_list) == 0 and not init_shutdown:
                init_shutdown = True
                shutdown_time = time.time() + 5.0

            # print self.outstanding_calls_list
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

                sim_name = msg.sender_id.get_sim_name()
                if (msg.__class__.__name__ == 'ServiceRequestMessage'):
                    try:
                        self._dispatch_service_request(msg)
                    except Exception:
                        self.exception('Error dispatching service request message.')
                        self.terminate_all_sims(status=Message.FAILURE)
                        #stop(self.timers['run'])
                        return False
                    continue
                elif (msg.__class__.__name__ == 'MethodResultMessage'):
                    if msg.call_id not in self.outstanding_calls_list:
                        self.task_manager.return_call(msg)
                        continue
                    # Message is a result from a framework invocation
                    self.outstanding_calls_list.remove(msg.call_id)
                    sim_msg_list = self.call_queue_map[msg.call_id]
                    del self.call_queue_map[msg.call_id]
                    if (msg.status == Message.FAILURE):
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
                        next_call_msg =  sim_msg_list.pop(0)
                        call_id = self.task_manager.init_call(next_call_msg,
                                                              manage_return=False)
                        self.outstanding_calls_list.append(call_id)
                        self.call_queue_map[call_id] = sim_msg_list
                    except IndexError:
                        sim_comps = self.config_manager.get_component_map() #Get any new dynamic simulations
                        if sim_name in sim_comps.keys():
                            self._send_monitor_event(sim_name, 'IPS_END',
                                                    comment, ok)
                            self._send_dynamic_sim_event(sim_name, 'IPS_END', ok)
                            self.send_terminate_msg(sim_name, Message.SUCCESS)
                            self.config_manager.terminate_sim(sim_name)
                            if self.ftb:
                                self._send_ftb_event('IPS_END')

        # SIMYAN: update the status of the simulation after all calls have
        # been executed
        main_fwk_comp = self.comp_registry.getEntry(fwk_comps[0])
        container_ext = main_fwk_comp.services.get_config_param('CONTAINER_FILE_EXT')
        self.container_file = os.path.basename(self.sim_root) + os.path.extsep + container_ext
        ipsutil.writeToContainer(self.container_file, self.sim_root, 'checklist.conf')

        self.terminate_all_sims(Message.SUCCESS)
        self.event_service._print_stats()
        #stop(self.timers['run'])
        #dumpAll()
        return True

    def initiate_new_simulation(self, sim_name):
        '''
        This is to be called by the configuration manager as part of dynamically creating
        a new simulation. The purpose here is to initiate the method invocations for the
        framework-visible components in the new simulation
        '''
        comp_list = self.config_manager.get_simulation_components(sim_name)
        msg_list = []
        self._send_monitor_event(sim_name, 'IPS_START', 'Starting IPS Simulation', ok= True)
        self._send_dynamic_sim_event(sim_name = sim_name, event_type = 'IPS_START')
        if self.ftb:
            self._send_ftb_event('IPS_START')
        for comp_id in comp_list:
            for method in ['init', 'step', 'finalize']:
                req_msg = ServiceRequestMessage(self.component_id,
                                                self.component_id, comp_id,
                                                'init_call', method, 0)
                msg_list.append(req_msg)

    # send off first round of invocations...
        msg = msg_list.pop(0)
        self.debug('Framework sending message %s ', msg.__dict__)
        call_id = self.task_manager.init_call(msg, manage_return=False)
        self.call_queue_map[call_id] = msg_list
        self.outstanding_calls_list.append(call_id)
        return

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
        if (self.verbose_debug):
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

        if (self.verbose_debug):
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

    def _send_dynamic_sim_event(self, sim_name = '', event_type = '', ok = True):
        self.debug('_send_dynamic_sim_event(%s:%s)',  event_type, sim_name)
        event_data = {}
        event_data['eventtype'] = event_type
        event_data['SIM_NAME'] = sim_name
        event_data['ok'] = ok
        topic_name = '_IPS_DYNAMIC_SIMULATION'
        self.debug('Publishing %s', str(event_data))
        self.event_manager.publish(topic_name, 'IPS_DYNAMIC_SIM', event_data)
        return

    def send_terminate_msg(self, sim_name, status= Message.SUCCESS):
        """
        Invoke terminate(status) on components in a simulation

        This method remotely invokes the method C{terminate()} on all componnets in the
        IPS simulation sim_name.
        """
        comp_ids = self.comp_registry.get_component_ids(sim_name)
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

    def terminate_all_sims(self, status= Message.SUCCESS):
        """
        Terminate all active component instances.

        This method remotely invokes the method C{terminate()} on all componnets in the
        IPS simulation.
        """
        #start(self.timers['terminate_all_sims'])
        sim_names = self.config_manager.get_sim_names()
        print 'Terminating ', sim_names
        for sim in sim_names:
            self.send_terminate_msg(sim, status)
        time.sleep(1)
        try:
            self.config_manager.terminate(status)
        except Exception, e:
            self.exception('exception encountered while cleaning up config_manager')
        #sys.exit(status)
        #stop(self.timers['terminate_sim'])

# SIMYAN: method for modifying the config file with the given parameter to
# the new value given
def modifyConfigObjFile(configFile,parameter,newValue,writeNew=True):
    # open the file, create the config object
    cfg_file = ConfigObj(configFile, interpolation='template', file_error=True)

    # modify the SIM_NAME value to the new value
    if cfg_file.has_key(parameter):
        cfg_file[parameter] = newValue
    else:
        print configFile + " has no parameter: "+parameter
        return ""

    newFileName = newValue + '.ips'
    newFile = open(newFileName, "w")
    if writeNew:
        cfg_file.write(newFile)    #write & close to avoid multiple references to these files
    else:
        cfg_file.write()

    return newFileName

# SIMYAN: method for extracting the needed files to the current directory
# for cloning runs from a container file
def extractIpsFile(containerFile,newSimName):
    """
    Given a container file, get the ips file in it and write it to current
    directory so that it can be used
    """
    oldIpsFile=os.path.splitext(containerFile)[0]+os.extsep+"ips"

    zf=zipfile.ZipFile(containerFile,"r")

    foundFile=""
    # Assume that container file contains 1 ips file.
    oldIpsFile=fnmatch.filter(zf.namelist(),"*.ips")[0]
    ifile=zf.read(oldIpsFile)
    ipsFile=newSimName+".ips"
    if os.path.exists(ipsFile):
        print "Moving "+ipsFile+" to "+"Save"+ipsFile
        shutil.copy(ipsFile, "Save"+ipsFile)
    ff=open(ipsFile,"w")
    ff.write(ifile)
    ff.close()
    return ipsFile

# callback function for options needing a file list
def filelist_callback(options, opt_str, values, parser):
    setattr(parser.values, options.dest, values.split(','))

def main(argv=None):
    """
    Check and parse args, create and run the framework.
    """
    # SIMYAN: setting options for command line invocation of the Framework
    runopts="[--create-runspace | --clone | --run-setup | --run] "
    fileopts="--simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME "
    miscopts="[--component=COMPONENT_FILE_NAME(S)] [--sim_name=SIM_NAME] [--log=LOG_FILE_NAME] "
    debugopts="[--debug | --ftb] [--verbose] "

    # SIMYAN: add the options to the options parser
    parser = optparse.OptionParser(usage="%prog "+runopts+debugopts+fileopts+miscopts)
    parser.add_option('-d','--debug',dest='debug', action='store_false',
                      help='Turn on debugging')
    parser.add_option('-v','--verbose',dest='verbose_debug', action='store_false',
                      help='Run IPS verbosely')
    parser.add_option('-f','--ftb',dest='ftb', action='store_false',
                      help='Turn on FTB capability')
    parser.add_option('-p', '--platform', dest='platform_filename', default='',
                      type="string", help='IPS platform configuration file')
    parser.add_option('-c', '--component',
                      action='callback', callback=filelist_callback,
                      type="string", help='IPS component configuration file(s)')
    parser.add_option('-i', '--simulation',
                      action='callback', callback=filelist_callback,
                      type="string", help='IPS simulation/config file')
    parser.add_option('-j', '--config',
                      action='callback', callback=filelist_callback,
                      type="string", help='IPS simulation/config file')
    parser.add_option('-y', '--clone',
                      action='callback', callback=filelist_callback,
                      type="string", help='Clone container file')
    parser.add_option('-e', '--sim_name',
                      action='callback', callback=filelist_callback,
                      type="string", help='Simulation name to replace in the IPS simulation file or a directory that has an ips file')
    parser.add_option('-l', '--log', dest='log_file', default='sys.stdout',
                      type="string", help='IPS Log file')
    parser.add_option('-n', '--nodes', dest='cmd_nodes', default='0',
                      type="int", help='Computer nodes')
    parser.add_option('-o', '--ppn', dest='cmd_ppn', default='0',
                      type="int", help='Computer processor per nodes')
    parser.add_option('-t','--create-runspace',dest='do_create_runspace', action='store_true',
                      help='Create the runspace')
    parser.add_option('-s','--run-setup',dest='do_run_setup', action='store_true',
                      help='Run the setup (init of the driver)')
    parser.add_option('-r','--run',dest='do_run', action='store_true',
                      help='Run')
    parser.add_option('-a','--all',dest='do_all', action='store_true',
                      help='Do all steps of the workflow')

    # SIMYAN: parse the options from command line
    options, args = parser.parse_args()
    # Default behavior : do all steps
    if options.do_create_runspace or \
        options.do_run_setup or \
        options.do_run:
        pass
    else:
        options.do_all = True

    ##-SIMYAN:----------------------------------------------------------------------------------
    ##
    ##  Three ways of specifying where to find the config_file
    ##   1. --simulation or --config: Specify directly
    ##   2. --sim_name: Either rename simulation files, or use sim_name/sim_name.ips
    ##   3. --clone: Look for IPS file in container file.  --sim_name must be specified to rename
    ##
    ##  See tests/refactor/test_ips.sh for motivation
    ##
    ##------------------------------------------------------------------------------------------
    ipsFilesToRemove=[]

    ### SIMYAN:
    ##  Some initial processing of the --simulation, --sim_name, clone
    ##  for basic checking and ease in processing better.
    #
    cfgFile_list = []
    usedSimulation=False
    if options.simulation:
        cfgFile_list=options.simulation
        nCfgFile=len(cfgFile_list)
        usedSimulation=True
    if options.config:
        cfgFile_list=options.config
        nCfgFile=len(cfgFile_list)

    # SIMYAN: grab the list of sim_names for multirun situations
    simName_list = []
    usedSim_name=False
    if options.sim_name:
        simName_list=options.sim_name
        nSimName=len(simName_list)
        usedSim_name=True
        if usedSimulation:
            if nSimName != nCfgFile and usedSimulation:
                print "When using both --simulation and --sim_name the list length must be the same"
                return

    # SIMYAN: grab the list of clone container files, and make sure the
    # new sim_names are given for each
    clone_list = []
    usedClone=False
    multiCloneSingleSource=False
    if options.clone:
        if not usedSim_name:
            print "Must specify SIM_NAME using --sim_name when cloning"
            return
        if usedSimulation:
            print "Cannot use both --simulation and --clone"
            return
        clone_list=options.clone
        nClone=len(clone_list)
        usedClone=True
        if nSimName > nClone and nClone == 1:
            #print "When using both --clone and --sim_name the list length must be the same"
            print 'Cloning from single clone file', clone_list[0], 'into multiple simulations', simName_list
            multiCloneSingleSource = True
            #return

    # SIMYAN: initialize list for each sim_name
    sim_file_map = {}
    for sim_name in simName_list:
        sim_file_map[sim_name] = []

    ### SIMYAN:
    ##  Now process the simulation files
    ##  Two methods for replacing the SIM_NAME:
    ##   1. colon syntax:   NEW_SIM_NAME:ips_file
    ##   2. sim_name parameter list
    #
    if usedSimulation:
        cleaned_file_list = []; ipsFilesToRemove= []
        # iterate over the list of files
        i=-1
        for file in cfgFile_list:
            # if the file name contains ':', we must replace SIM_NAME in the
            # file with the new value and remove the new SIM_NAME and ':'
            # from the string for IPS to read the modified .ips file.
            if file.find(':') != -1:
                # split the mapping.  new_sim_name gets replaced below
                (new_sim_name, file_name) = file.split(':')
                if usedSim_name:
                    file=modifyConfigObjFile(file_name,'SIM_NAME',new_sim_name)
                    ipsFilesToRemove.append(file)
                    sim_file_map[new_sim_name].append(file)
                else:
                    iFile=modifyConfigObjFile(file,'SIM_NAME',new_sim_name,)
                    #ipsFilesToRemove.append(file)

            if usedSim_name:
                i=i+1
                new_sim_name=simName_list[i]
                file=modifyConfigObjFile(file,'SIM_NAME',new_sim_name)
                ipsFilesToRemove.append(file)
                sim_file_map[new_sim_name].append(file)

            # append file to the list of cleaned names that don't contain ':'
            cleaned_file_list.append(file)

        # replace cfgFile_list with a list that won't have any ':' or sim_names
        cfgFile_list = cleaned_file_list


    ### SIMYAN:
    ##  Now process container files when cloning
    #
    if usedClone:
        options.do_create_runspace=True
        cleaned_file_list = []
        # iterate over the list of files
        i=-1
        for clone_file in clone_list:
            if multiCloneSingleSource:
                for new_sim_name in simName_list:
                    iFile=extractIpsFile(clone_file,new_sim_name)
                    file=modifyConfigObjFile(iFile,'SIM_NAME',new_sim_name,writeNew=False)
                    sim_file_map[new_sim_name].append(iFile)
                    cleaned_file_list.append(iFile)
            else:
                i=i+1
                new_sim_name=simName_list[i]
                print 'else'
                iFile=extractIpsFile(clone_file,new_sim_name)
                file=modifyConfigObjFile(iFile,'SIM_NAME',new_sim_name,writeNew=False)
                sim_file_map[new_sim_name].append(iFile)
                # append file to the list of cleaned names that don't contain ':'
                cleaned_file_list.append(iFile)


        # replace cfgFile_list with a list that won't have any ':' or sim_names
        cfgFile_list = cleaned_file_list
        ipsFilesToRemove=cleaned_file_list


    ### SIMYAN:
    ##  sim_name specified without simulation or clone means
    ##  look for the IPS file in sim_name subdirectory
    #
    if usedSim_name and not (usedSimulation or usedClone):
        cleaned_file_list = []
        for simname in simName_list:
            new_file_name=os.path.join(simname,simname+".ips")
            foundFile=""
            for testFile in glob.glob(simname+"/*.ips"):
                cfg_file = ConfigObj(testFile,interpolation='template')
                if cfg_file.has_key("SIM_NAME"):
                    testSimName=cfg_file["SIM_NAME"]
                    if testSimName == simname:
                        foundFile=testFile
                        sim_file_map[sim_name].append(foundFile)

            print "FOUND FILE", foundFile
            if foundFile:
                cleaned_file_list.append(foundFile)
            else:
                print "Cannot find ips file associated with SIM_NAME= ", simname
                return

        cfgFile_list = cleaned_file_list

    # SIMYAN: process component files
    compset_list = []
    if options.component:
        compset_list=options.component

    if options.do_all:
        #print 'doing all steps'
        options.do_create_runspace = True
        options.do_run_setup = True
        options.do_run = True

    try:
        # SIMYAN: added logic to handle multiple runs in sequence
        if simName_list:
            for sim_name in simName_list:
                cfgFile_list = sim_file_map[sim_name]
                fwk = Framework(options.do_create_runspace, options.do_run_setup, options.do_run,
                      cfgFile_list, options.log_file, options.platform_filename,
                      compset_list, options.debug, options.ftb, options.verbose_debug,
                      options.cmd_nodes, options.cmd_ppn)
                fwk.run
            ipsTiming.dumpAll('framework')
        else:
            fwk = Framework(options.do_create_runspace, options.do_run_setup, options.do_run,
                  cfgFile_list, options.log_file, options.platform_filename,
                  compset_list, options.debug, options.ftb, options.verbose_debug,
                  options.cmd_nodes, options.cmd_ppn)
            fwk.run
            ipsTiming.dumpAll('framework')
    except :
        raise

    # SIMYAN: post running cleanup of working files, so there aren't
    # leftover files from doing clones or renaming simulations
    if len(ipsFilesToRemove)>0:
        for file in ipsFilesToRemove:
            os.remove(file)

    return 0

# ----- end main -----

if __name__ == "__main__":
    print "Starting IPS"
    sys.stdout.flush()
    sys.exit(main())
