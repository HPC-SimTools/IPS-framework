#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import messages
import sys
import Queue
import os
import subprocess

import time
import ipsutil
import shutil
import string
from cca_es_spec import initialize_event_service
from ips_es_spec import eventManager
import logging
import logging.handlers
import ipsLogging
import signal
import ipsTiming
from configobj import ConfigObj
import glob
import ipsExceptions
import ipsTiming
from symbol import except_clause
import weakref

MY_VERSION = float(sys.version[:3])
#import pytau

def make_timers_parent():
    """
    Create a list of timers to be applied to methods executed before the new component
    object is forked into its own separate process.
    """
    pid = str(os.getpid())
    return {'__init__':ipsTiming.create_timer("services", "__init__", pid),
            'get_config_param':ipsTiming.create_timer("services", "get_config_param", pid),
            '__initialize__':ipsTiming.create_timer("services", "__initialize__", pid)}

def make_timers_child():
    """
    Create a list of timers to be applied to methods executed after the new component
    object is forked into its own separate process.
    """
    pid = str(os.getpid())
    return {'_init_event_service':ipsTiming.create_timer("services", "_init_event_service", pid),
            '_get_elapsed_time':ipsTiming.create_timer("services", "_get_elapsed_time", pid),
            '_get_incoming_responses':ipsTiming.create_timer("services", "_get_incoming_responses", pid),
            '_wait_msg_response':ipsTiming.create_timer("services", "_wait_msg_response", pid),
            '_invoke_service':ipsTiming.create_timer("services", "invoke_service", pid),
            '_get_service_response':ipsTiming.create_timer("services", "_get_service_response", pid),
            '_send_monitor_event':ipsTiming.create_timer("services", "_send_monitor_event", pid),
            'get_port':ipsTiming.create_timer("services", "get_port", pid),
            'call_nonblocking':ipsTiming.create_timer("services", "call_nonblocking", pid),
            'call':ipsTiming.create_timer("services", "call", pid),
            'wait_call':ipsTiming.create_timer("services", "wait_call", pid),
            'wait_call_list':ipsTiming.create_timer("services", "wait_call_list", pid),
            'launch_task':ipsTiming.create_timer("services", "launch_task", pid),
            'kill_task':ipsTiming.create_timer("services", "kill_task", pid),
            'kill_all_tasks':ipsTiming.create_timer("services", "kill_all_tasks", pid),
            'wait_task_nonblocking':ipsTiming.create_timer("services", "wait_task_nonblocking", pid),
            'wait_task':ipsTiming.create_timer("services", "wait_task", pid),
            'wait_tasklist':ipsTiming.create_timer("services", "wait_tasklist", pid),
            'get_config_param':ipsTiming.create_timer("services", "get_config_param", pid),
            'get_time_loop':ipsTiming.create_timer("services", "get_time_loop", pid),
            'get_working_dir':ipsTiming.create_timer("services", "get_working_dir", pid),
            'stage_input_files':ipsTiming.create_timer("services", "stage_input_files", pid),
            'stage_data_files':ipsTiming.create_timer("services", "stage_data_files", pid),
            'stage_output_files':ipsTiming.create_timer("services", "stage_output_files", pid),
            'stage_nonPS_output_files':ipsTiming.create_timer("services", "stage_nonPS_output_files", pid),
            'stage_PS_output_files':ipsTiming.create_timer("services", "stage_PS_output_files", pid),
            'stage_plasma_state':ipsTiming.create_timer("services", "stage_plasma_state", pid),
            'update_plasma_state':ipsTiming.create_timer("services", "update_plasma_state", pid),
            'update_time_stamp':ipsTiming.create_timer("services", "update_time_stamp", pid),
            'setMonitorURL':ipsTiming.create_timer("services", "setMonitorURL", pid)}


class ServicesProxy(object):

    def __init__(self, fwk, fwk_in_q, svc_response_q, sim_conf, log_pipe_name):
        """
        The *ServicesProxy* object is responsible for marshalling invocations
        of framework services to the framework process using a shared queue.
        The queue is shared among all components in a simulation. The results
        from framework services invocations are received via another,
        component-specific "framework response" queue.

        Create a new ServicesProxy object

        *fwk*: Enclosing IPS simulation framework, of type
               :py:meth:`ips.Framework`
        *fwk_in_q*: Framework input message queue - shared among all service
                    objects
        *svc_response_q*: Service response message queue - one per service
                          object.
        *sim_conf*: Simulation configuration dictionary, contains data from
                    the simulation configuration file merged with the platform
                    configuration file.
        *log_pipe_name*: Name of logging pipe for use by the IPS logging
                         daemon.
        """
        self.pid = 0
        self.fwk = fwk
        self.fwk_in_q = fwk_in_q
        self.svc_response_q = svc_response_q
        self.sim_conf = sim_conf
        self.log_pipe_name = log_pipe_name
        self.component_ref = None
        self.incomplete_calls = {}
        self.finished_calls = {}
        self.task_map = {}
        self.workdir = ''
        self.full_comp_id = ''
        self.logger = None
        self.start_time = time.time()
        self.cur_time = self.start_time
        self.event_service = None
        self.counter = 0
        self.monitor_url = None
        self.call_targets = {}
        self.task_pools = {}
        self.time_loop = None
        self.last_ckpt_walltime = self.start_time
        self.last_ckpt_phystime = None
        self.new_chkpts = []
        self.protected_chkpts = []
        self.chkpt_counter = 0
        self.sim_name = ''
        self.replay_conf = None
        self.profile = False
        self.subflow_count = 0
        self.sub_flows = {}
        self.binary_fullpath_cache = {}
        try:
            if os.environ['IPS_TIMING'] == '1':
                self.profile = True
        except:
            pass
        ipsTiming.instrument_object_with_tau('services', self, exclude = ['__init__'])

    def _make_timers(self):
        ipsTiming.instrument_object_with_tau('services', self, exclude = ['__init__'])


    def __initialize__(self, component_ref):
        """
        Initialize the service proxy object, connecting it to its associated
        component.

        This method is for use only by the IPS framework.
        """

        self.component_ref = weakref.proxy(component_ref)
        conf = self.component_ref.config
        self.full_comp_id =  '_'.join([conf['CLASS'], conf['SUB_CLASS'],
                                       conf['NAME'],
                                       str(self.component_ref.component_id.get_seq_num())])
        #
        # Set up logging path to the IPS logging daemon
        #
        socketHandler = ipsLogging.IPSLogSocketHandler(self.log_pipe_name)
        self.logger = logging.getLogger(self.full_comp_id)
        log_level = 'WARNING'
        try:
            log_level = conf['LOG_LEVEL']
            # print 'Setting log_level to ', log_level, 'From component config'
        except KeyError:
            try:
                log_level = self.sim_conf['LOG_LEVEL']
                # print 'Setting log_level to ', log_level, 'From master config'
            except KeyError:
                pass
        try:
            real_log_level = getattr(logging, log_level)
            # print 'Setting real log level to ', real_log_level
        except AttributeError:
            # print 'Invalid LOG_LEVEL value :', log_level
            raise
        self.logger.setLevel(real_log_level)
        self.logger.addHandler(socketHandler)
        self.debug('__initialize__(): %s  %s ',
                    str(self.component_ref), str(self.component_ref.component_id))
        self.sim_name = self.component_ref.component_id.get_sim_name()
        # ------------------
        # set shared_nodes
        # ------------------
        try:
            pn_compconf = conf['NODE_ALLOCATION_MODE']
            if pn_compconf.upper() == 'SHARED':
                self.shared_nodes = True
            elif pn_compconf.upper() == 'EXCLUSIVE':
                self.shared_nodes = False
            else:
                self.fwk.exception("Bad 'NODE_ALLOCATION_MODE' value %s" % pn_compconf)
                raise("Bad 'NODE_ALLOCATION_MODE' value %s" % pn_compconf)
        except:
            if self.sim_conf['NODE_ALLOCATION_MODE'] == 'SHARED':
                self.shared_nodes = True
            else:
                self.shared_nodes = False

        # ------------------
        # set component ppn
        # ------------------
        try:
            self.ppn = int(conf['PROCS_PER_NODE'])
        except:
            self.ppn = 0

        if self.sim_conf['SIMULATION_MODE'] == 'RESTART':
            if self.sim_conf['RESTART_TIME'] == 'LATEST':
                chkpts = glob.glob(os.path.join(self.sim_conf['RESTART_ROOT'], 'restart', '*'))
                base_dir = sorted(chkpts, key=lambda d: float(os.path.basename(d)))[-1]
                self.sim_conf['RESTART_TIME'] = os.path.basename(base_dir)


    def _init_event_service(self):
        """
        Initialize connection to the central framework event service
        """
        self.debug('_init_event_service(): self.counter = %d - %s',
                   self.counter, str(self.component_ref))
        self.counter = self.counter + 1
        initialize_event_service(self)
        self.event_service = eventManager(self.component_ref)
        return

    def _get_elapsed_time(self):
        """
        Return total elapsed time since simulation started in seconds
        (including a possible fraction)
        """
        self.cur_time = time.time()
        delta_t = self.cur_time - self.start_time
        return delta_t

    def _get_incoming_responses(self, block=False):
        """
        Get all pending responses on the service response queue.

        *block*: Boolean flag. If ``True``, block waiting for one or more
        responses to arrive. When *block* is false, return immediately with
        a (possibly empty) list of available responses.

        Return a (possibly empty) list of service response messages objects
        (:py:meth:`messages.ServiceResponseMessage`)
        """
        response_list = []
        finish = False
        timeout = 0.01
        while(not finish):
            try:
                response = self.svc_response_q.get(block, timeout)
                response_list.append(response)
            except Queue.Empty:
                if (not block):
                    finish = True
                elif (len(response_list) > 0):
                    finish = True
#        dumpAll()
        return response_list


    def _wait_msg_response(self, msg_id, block=True):
        """
        Wait for a service response message that corresponds to service
        request message *msg_id*.  If *block* is ``True``, then the method
        will block until a response for *msg_id* is received.  Otherwise,
        return immediately if no response is readily available.  Return
        :py:meth:`messages.ServiceResponseMessage` when available, otherwise
        ``None``.
        """
        #print 'in _wait_msg_response'
        if (msg_id in self.finished_calls.keys()):
            response = self.finished_calls[msg_id]
            del self.finished_calls[msg_id]
            return response
        elif (msg_id not in self.incomplete_calls.keys()):
            self.error('Invalid call ID : %s ', str(msg_id))
            raise Exception('Invalid message request ID argument')

        keep_going = True
        while keep_going:
            # get new messages, block until something interesting comes along
            responses = self._get_incoming_responses(block)
            for r in responses:
                # time to die!
                if (r.__class__ == messages.ExitMessage):
                    self.debug('%s Exiting', str(self.component_ref.component_id))
                    self._cleanup()
                    if (r.status == messages.Message.SUCCESS):
                        sys.exit(0)
                    else:
                        sys.exit(1)
                # response to my message
                elif (r.__class__ == messages.ServiceResponseMessage):
                    if (r.request_msg_id not in
                        self.incomplete_calls.keys()):
                        self.error('Mismatched service response msg_id %s',
                                   str(r.request_msg_id))
#                        dumpAll()
                        raise Exception('Mismatched service response msg_id.')
                    else:
                        del self.incomplete_calls[msg_id]
                        self.finished_calls[r.request_msg_id] = r
                        if (r.request_msg_id == msg_id):
                            keep_going = False
                # some weird message came through
                else:
                    self.error('Unexpected service response of type %s',
                               r.__class__.__name__)
#                    dumpAll()
                    raise Exception('Unexpected service response of type ' +
                               r.__class__.__name__)

            if (not block):
                keep_going = False
        # if this message corresponds to a finish invocation, return the response message
        if (msg_id in self.finished_calls.keys()):
            response = self.finished_calls[msg_id]
            del self.finished_calls[msg_id]
#            dumpAll()
            return response
#        dumpAll()
        return None


    def _invoke_service(self, component_id, method_name, *args, **keywords):
        """
        Create and place in the ``self.fwk_in_q`` a new
        :py:meth:`messages.ServiceRequestMessage` for service
        *method_name* with *\*args* arguments on behalf of component
        *component_id*.  Return message id.
        """
        self.debug('_invoke_service(): %s  %s', method_name, str(args[0:]))
        new_msg = messages.ServiceRequestMessage(self.component_ref.component_id,
                                                 self.fwk.component_id,
                                                 component_id,
                                                 method_name, *args, **keywords)
        msg_id = new_msg.get_message_id()
        self.incomplete_calls[msg_id] = new_msg
        self.fwk_in_q.put(new_msg)
        return msg_id

    def _get_service_response(self, msg_id, block=True):
        """
        Return response from message *msg_id*.  Calls
        :py:meth:`ServicesProxy._wait_msg_response` with *msg_id* and *block*.  If response
        is not present, ``None`` is returned, otherwise the response is passed
        on to the component.  If the status of the response is failure
        (``Message.FAILURE``), then the exception body is raised.
        """
        #print "in _get_service_response"
        self.debug('_get_service_response(%s)', str(msg_id))
        response = self._wait_msg_response(msg_id, block)
        self.debug('_get_service_response(%s), response = %s', str(msg_id), str(response))
        if (response == None):
            return None
        if (response.status == messages.Message.FAILURE):
            self.debug('###### Raising %s', str(response.args[0]))
            raise response.args[0]
        if (len(response.args) > 1):
            return response.args
        else:
            return response.args[0]

    def _send_monitor_event(self,
                            eventType='',
                            comment='',
                            ok='True',
                            state='Running'):
        """
        Construct and send an event populated with the component's
        information, *eventType*, *comment*, *ok*, *state*, and a wall time
        stamp, to the portal bridge to pass on to the web portal.
        """
        portal_data = {}
        portal_data['code'] = '_'.join([self.component_ref.CLASS,
                                      self.component_ref.SUB_CLASS,
                                      self.component_ref.NAME])
        portal_data['eventtype'] = eventType
        portal_data['ok'] = ok
        portal_data['walltime'] = '%.2f' % (time.time() - self.component_ref.start_time)
        portal_data['state'] = state
        portal_data['comment'] = comment
        if(self.monitor_url):
            portal_data['vizurl'] = self.monitor_url.split('//')[-1]

        event_data = {}
        event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTAL_EVENT', event_data)
        return

    def _cleanup(self):
        """
        Clean up any state from the services.  Called by the terminate method
        in the base class for components.
        """
        # add anything else to clean up in the services
        if self.profile:
            ipsTiming.dumpAll('component')

    def get_port(self, port_name):
        """
        Return a reference to the component implementing port *port_name*.
        """
        msg_id = self._invoke_service(self.fwk.component_id,
                            'get_port', port_name)
        response = self._get_service_response(msg_id, True)
        return response

    def getPort(self, port_name):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.get_port`
        """
        self.warning('getPort() deprecated - use get_port() instead')
        return self.get_port(port_name)

    def call_nonblocking(self, component_id, method_name, *args, **keywords):
        """
        Invoke method *method_name* on component *component_id* with optional
        arguments *\*args*.  Return *call_id*.
        """
        target_class = component_id.get_class_name()
        target_seqnum = component_id.get_seq_num()
        target = target_class + '@' + str(target_seqnum)
        formatted_args = ['%.3f' % (x) if isinstance(x, float)
                                        else str(x) for x in args]
        if keywords:
            formatted_args += ["%s=" % k  + str(v) for (k,v) in keywords.iteritems()]
        self._send_monitor_event('IPS_CALL_BEGIN', 'Target = ' +
                                 target + ':' + method_name +'('+
                                 ' ,'.join(formatted_args) + ')')
        msg_id = self._invoke_service(component_id,
                                       'init_call',
                                       method_name, *args, **keywords)
        call_id = self._get_service_response(msg_id, True)
        self.call_targets[call_id] = (target, method_name, args)
        return call_id

    def call(self, component_id, method_name, *args, **keywords):
        """
        Invoke method *method_name* on component *component_id* with optional
        arguments *\*args*.  Return result from invoking the method.
        """
        call_id = self.call_nonblocking(component_id, method_name, *args, **keywords)
        retval = self.wait_call(call_id, block=True)
        return retval

    def wait_call(self, call_id, block=True):
        """
        If *block* is ``True``, return when the call has completed with the
        return code from the call.
        If *block* is ``False``, raise
        :py:exc:`ipsExceptions.IncompleteCallException` if the call has not
        completed, and the return value is it has.
        """
        try:
            (target, method_name, args) = self.call_targets[call_id]
        except KeyError:
            self.exception('Invalid call_id in wait-call() : %s', call_id)
            raise
        msg_id = self._invoke_service(self.fwk.component_id, 'wait_call',
                                      call_id, block)
        response = self._get_service_response(msg_id, block=True)
        formatted_args = ['%.3f' % (x) if isinstance(x, float)
                                        else str(x) for x in args]
        self._send_monitor_event('IPS_CALL_END', 'Target = ' +
                                          target + ':' + method_name +'('+
                                          str(*formatted_args) + ')')
        del self.call_targets[call_id]
        return response

    def wait_call_list(self, call_id_list, block=True):
        """
        Check the status of each of the call in *call_id_list*.  If *block* is
        ``True``, return when *all* calls are finished.  If *block* is
        ``False``, raise :py:exc:`ipsExceptions.IncompleteCallException` if
        *any* of the calls have not completed, otherwise return.  The return
        value is a dictionary of *call_ids* and return values.
        """
        ret_map = {}
        caught_exceptions = []
        for call_id in call_id_list:
            try:
                ret_val = self.wait_call(call_id, block)
            except Exception, e:
                self.exception('Caught exception in wait_call()')
                caught_exceptions.append(e)
            else:
                if (ret_val != None):
                    ret_map[call_id] = ret_val
        if len(caught_exceptions) > 0:
            self.error('Caught one or more exceptions in call to wait_call_list')
            raise e
        return ret_map

    def launch_task(self, nproc, working_dir, binary, *args, **keywords):
        """
        Launch *binary* in *working_dir* on *nproc* processes.  *\*args* are
        any arguments to be passed to the binary on the command line.
        *\*\*keywords* are any keyword arguments used by the framework to
        manage how the binary is launched.  Keywords may be the following:

            * *task_ppn* : the processes per node value for this task
            * *block* : specifies that this task will block (or raise an
              exception) if not enough resources are available to run
              immediately.  If ``True``, the task will be retried until it
              runs.  If ``False``, an exception is raised indicating that
              there are not enough resources, but it is possible to eventually
              run.  (default = ``True``)
            * *tag* : identifier for the portal.  May be used to group related
              tasks.
            * *logfile* : file name for ``stdout`` (and ``stderr``) to be
              redirected to for this task.  By default ``stderr`` is
              redirected to ``stdout``, and ``stdout`` is not redirected.
            * *whole_nodes* : if ``True``, the task will be given exclusive
              access to any nodes it is assigned.  If ``False``, the task may
              be assigned nodes that other tasks are using or may use.
            * *whole_sockets* : if ``True``, the task will be given exclusive
              access to any sockets of nodes it is assigned.  If ``False``,
              the task may be assigned sockets that other tasks are using or
              may use.

        Return *task_id* if successful.  May raise exceptions related to
        opening the logfile, being unable to obtain enough resources to launch
        the task (:exc:`ipsExceptions.InsufficientResourcesException`), bad
        task launch request
        (:exc:`ipsExceptions.ResourceRequestMismatchException`,
        :exc:`ipsExceptions.BadResourceRequestException`) or problems
        executing the command. These exceptions may be used to retry launching
        the task as appropriate.

        .. note :: This is a nonblocking function, users must use a version of :py:meth:`ServicesProxy.wait_task` to get result.

        """
        tokens = binary.split()
        if len(tokens) > 1 :
            binary = tokens[0]
            args = tuple(tokens[1:]) + args
        try:
            binary_fullpath = self.binary_fullpath_cache[binary]
        except KeyError:
            binary_fullpath = ipsutil.which(binary)
        if not binary_fullpath:
            self.error("Program %s is not in path or is not executable" % binary)
            raise Exception("Program %s is not in path or is not executable" % binary)
        else:
            self.binary_fullpath_cache[binary] = binary_fullpath

        task_ppn = self.ppn
        try:
            task_ppn = keywords['task_ppn']
        except:
            pass

        block = True
        try:
            block = keywords['block']
        except:
            pass

        tag = 'None'
        try:
            tag = keywords['tag']
        except:
            pass

        try:
            whole_nodes = keywords['whole_nodes']
            #print ">>>> value of whole_nodes", whole_nodes
        except:
            if self.shared_nodes == True:
                whole_nodes = False
            else:
                whole_nodes = True

        try:
            whole_socks = keywords['whole_sockets']
            #print ">>>> value of whole_socks", whole_socks
        except:
            if self.shared_nodes == True:
                whole_socks = False
            else:
                whole_socks = True

        #print "about to call init task"
        try:
            # SIMYAN: added working_dir to component method invocation
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'init_task', nproc, binary_fullpath,
                                          working_dir, task_ppn, block,
                                          whole_nodes, whole_socks, *args)
            (task_id, command, env_update) = self._get_service_response(msg_id, block=True)
        except Exception, e:
            #self.exception('Error initiating task %s %s on %d nodes' %  (binary, str(args), int(nproc)))
            raise

        log_filename = None
        try:
            log_filename = keywords['logfile']
        except KeyError:
            pass

        task_stdout = sys.stdout
        if (log_filename):
            try:
                task_stdout = open(log_filename, 'w')
            except:
                self.exception('Error opening log file %s : using stdout', log_filename)

        cmd_lst = command.split(' ')
        if not cmd_lst[-1]:
            # Kill the last argument in the command list if it is the empty string
            cmd_lst.pop()

        try:
            self.debug('Launching command : %s', command)
            if env_update:
                new_env = os.environ
                new_env.update(env_update)
                process = subprocess.Popen(cmd_lst, stdout = task_stdout,
                                           stderr = subprocess.STDOUT,
                                           cwd = working_dir,
                                           env = new_env)
            else:
                process = subprocess.Popen(cmd_lst, stdout = task_stdout,
                                           stderr = subprocess.STDOUT,
                                           cwd = working_dir)
        except Exception, e:
            self.exception('Error executing command : %s', command)
            raise
        self._send_monitor_event('IPS_LAUNCH_TASK', 'task_id = %s , Tag = %s , nproc = %d , Target = %s'  % \
                                      (str(task_id), tag, int(nproc), command))

        # FIXME: process Monitoring Command : ps --no-headers -o pid,state pid1  pid2 pid3 ...

        self.task_map[task_id] = (process, time.time())
        return task_id #process.pid

    def launch_task_resilient(self, nproc, working_dir, binary, *args, **keywords):
        """
        **not used**
        """
        task_ppn = self.ppn
        try:
            task_ppn = keywords['task_ppn']
        except:
            pass

        block = True
        try:
            block = keywords['block']
        except:
            pass
        wnodes = keywords['whole_nodes']
        wsocks = keywords['whole_sockets']

        try:
            # SIMYAN: added working_dir to component method invocation
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'init_task', nproc, binary,
                                          working_dir, task_ppn,
                                          block, wnodes, wsocks, *args)
            (task_id, command, env_update) = self._get_service_response(msg_id, block=True)
        except Exception, e:
            self.exception('Error initiating task %s %s on %d nodes' % \
                                (binary, str(args), int(nproc)))
            raise

        log_filename = None
        try:
            log_filename = keywords['logfile']
        except KeyError:
            pass

        task_stdout = sys.stdout
        if (log_filename):
            try:
                task_stdout = open(log_filename, 'w')
            except:
                self.exception('Error opening log file %s : using stdout', log_filename)

        cmd_lst = command.split(' ')
        try:
            self.debug('Launching command : %s', command)
            if env_update:
                new_env = os.environ
                new_env.update(env_update)
                process = subprocess.Popen(cmd_lst, stdout = task_stdout,
                                           stderr = subprocess.STDOUT,
                                           cwd = working_dir,
                                           env = new_env)
            else:
                process = subprocess.Popen(cmd_lst, stdout = task_stdout,
                                           stderr = subprocess.STDOUT,
                                           cwd = working_dir)
        except Exception, e:
            self.exception('Error executing command : %s', command)
            raise
        self._send_monitor_event('IPS_LAUNCH_TASK', 'Target = ' + command + \
                                 ', task_id = ' + str(task_id))

        # FIXME: process Monitoring Command : ps --no-headers -o pid,state pid1
        # pid2 pid3 ...

        self.task_map[task_id] = (process,time.time(),nproc,working_dir,binary,
                                  args,keywords)
        return task_id #process.pid

    def launch_task_pool(self, task_pool_name):
        """
        Construct messages to task manager to launch each task.
        Used by :py:class:`TaskPool` to launch tasks in a task_pool.
        """

        task_pool = self.task_pools[task_pool_name]
        queued_tasks = task_pool.queued_tasks
        submit_dict = {}
        for (task_name, task) in queued_tasks.iteritems():
            #(nproc, working_dir, binary, args, keywords) = queued_tasks[task_name]
            task_ppn = self.ppn
            try:
                task_ppn = task.keywords['task_ppn']
            except:
                pass
            try:
                wnodes = task.keywords['whole_nodes']
            except:
                if self.shared_nodes == True:
                    wnodes = False
                else:
                    wnodes = True
            try:
                wsocks = task.keywords['whole_sockets']
            except:
                if self.shared_nodes == True:
                    wsocks = False
                else:
                    wsocks = True
            submit_dict[task_name] = (task.nproc, task.working_dir,
                                      task.binary, task.args,
                                      task_ppn, wnodes, wsocks)

        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'init_task_pool', submit_dict)
            allocated_tasks = self._get_service_response(msg_id, block=True)
        except Exception, e:
            self.exception('Error initiating task pool %s ', task_pool_name)
            raise

        active_tasks = {}
        for task_name in allocated_tasks.keys():
            #(nproc, working_dir, binary, args, keywords) = queued_tasks[task_name]
            task = queued_tasks[task_name]
            (task_id, command, env_update) = allocated_tasks[task_name]
            tag = 'None'
            try:
                tag = task.keywords['tag']
            except KeyError:
                pass

            log_filename = None
            try:
                log_filename = task.keywords['logfile']
            except KeyError:
                pass

            task_stdout = sys.stdout
            if (log_filename):
                try:
                    task_stdout = open(log_filename, 'w')
                except:
                    self.exception('Error opening log file %s : using stdout', log_filename)

            cmd_lst = command.split(' ')
            try:
                self.debug('Launching command : %s', command)
                if env_update:
                    new_env = os.environ
                    new_env.update(env_update)
                    process = subprocess.Popen(cmd_lst, stdout = task_stdout,
                                               stderr = subprocess.STDOUT,
                                               cwd = task.working_dir,
                                               env = new_env)
                else:
                    process = subprocess.Popen(cmd_lst, stdout = task_stdout,
                                               stderr = subprocess.STDOUT,
                                               cwd = task.working_dir)
            except Exception, e:
                self.exception('Error executing task %s - command : %s', task_name, command)
                raise
            self._send_monitor_event('IPS_LAUNCH_TASK_POOL', 'task_id = %s , Tag = %s , nproc = %d , Target = %s , task_name = %s'  % \
                                      (str(task_id), str(tag), int(task.nproc), command, task_name))

            self.task_map[task_id] = (process, time.time())
            active_tasks[task_name] = task_id
        return active_tasks

    def kill_task(self, task_id):
        """
        Kill launched task *task_id*.  Return if successful.  Raises exceptions if the task or process cannot be found or killed successfully.
        """
        try:
            process, start_time = self.task_map[task_id]
            #TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
            #process, start_time = self.task_map[task_id][0], self.task_map[task_id][1]
        except KeyError, e:
            self.exception('Error: unrecognizable task_id = %s ', task_id)
            raise # do we really want to raise an error or just return?
        task_retval = 'killed'
        # kill process
        try:
            if MY_VERSION < 2.6:
                os.kill(process.pid, signal.SIGTERM)
            else:
                process.terminate()
        except Exception, e:
            self.exception('exception during process termination for task %d', task_id)
            raise

        del self.task_map[task_id]
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'finish_task', task_id, task_retval)
            retval = self._get_service_response(msg_id, block=True)
        except Exception, e:
            self.exception('Error finalizing task  %s' , task_id)
            raise
        return

    def kill_all_tasks(self):
        """
        Kill all tasks associated with this component.
        """
        while len(self.task_map) > 0:
            try:
                self.kill_task(self.task_map[0])
            except Exception, e:
                raise
        return

    def wait_task_nonblocking(self, task_id):
        """
        Check the status of task *task_id*.  If it has finished, the return value is populated with the actual value, otherwise ``None`` is returned.  A *KeyError* exception may be raised if the task is not found.
        """
        try:
            process, start_time = self.task_map[task_id]
            #TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
            #process, start_time = self.task_map[task_id][0], self.task_map[task_id][1]
        except KeyError, e:
            self.exception('Error: unrecognizable task_id = %s ', task_id)
            raise
        task_retval = process.poll()
        if task_retval == None:
            return None
        else:
            retval = self.wait_task(task_id)
            return retval

    def wait_task(self, task_id):
        """
        Check the status of task *task_id*.  Return the return value of the task when finished successfully.  Raise exceptions if the task is not found, or if there are problems finalizing the task.
        """
        print "in wait task"
        try:
            process, start_time = self.task_map[task_id]
        except KeyError, e:
            self.exception('Error: unrecognizable task_id = %s ', str(task_id))
            raise
        task_retval = process.wait()
        self._send_monitor_event('IPS_TASK_END', 'task_id = %s  elapsed time = %.2f S' %
                                 (str(task_id), time.time() - start_time))

        del self.task_map[task_id]
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'finish_task', task_id, task_retval)
            retval = self._get_service_response(msg_id, block=True)
        except Exception, e:
            self.exception('Error finalizing task  %s' , task_id)
            raise
        return task_retval

    def wait_task_resilient(self, task_id):
        """
        **not used**
        """
        try:
            process,start_time,nproc,working_dir,binary,args,keywords = self.task_map[task_id]
        except KeyError, e:
            self.exception('Error: unrecognizable task_id = %s ', str(task_id))
            raise
        task_retval = process.wait()
        self._send_monitor_event('IPS_TASK_END', 'task_id = %s  elapsed time = %.2f S' %
                                 (str(task_id), time.time() - start_time))

        del self.task_map[task_id]
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'finish_task', task_id, task_retval)
            retval = self._get_service_response(msg_id, block=True)
        except Exception, e:
            self.exception('Error finalizing task  %s' , task_id)
            raise

        if task_retval == 0:
            if retval == 0:
                self.debug('Successful execution and no FTB trace.')
            elif retval == 1:
                self.debug('Successful execution and FTB trace.')
        else:
            if retval == 0:
                self.error('Unsuccessful execution and no FTB trace.')
                raise Exception('Execution failed presumably due to application error.')
            elif retval == 1:
                self.exception('Unsuccessful execution and FTB trace.')
                if (not keywords.has_key('relaunch')) or (keywords['relaunch'] != 'N'):
                    relaunch_task_id = self.launch_task_resilient(nproc, working_dir, binary, args, keywords)
                    self.debug('Relaunched failed task.')
                    return self.wait_task_resilient(relaunch_task_id)
                else:
                    self.debug('Task failed but was not relaunched.')

        return task_retval

    def wait_tasklist(self, task_id_list, block = True):
        """
        Check the status of a list of tasks.  If *block* is ``True``, return a
        dictionary of return values when *all* tasks have completed.  If
        *block* is ``False``, return a dictionary containing entries for each
        *completed* task.  Note that the dictionary may be empty.  Raise
        *KeyError* exception if *task_id* not found.

        """
        ret_dict = {}
        running_tasks = [task_id for task_id in task_id_list]
        for task_id in task_id_list:
            try:
                process = self.task_map[task_id][0]
            except KeyError:
                self.exception('Error: unknown task id : %s', task_id)
                raise
        while (len(running_tasks) > 0) :
            for task_id in task_id_list:
                if task_id not in running_tasks:
                    continue
                process = self.task_map[task_id][0]
                retval = process.poll()
                if (retval != None):
                    task_retval = self.wait_task(task_id)
                    ret_dict[task_id] = task_retval
                    running_tasks.remove(task_id)
            if not block:
                break
            time.sleep(0.05)
        return ret_dict

    def get_config_param(self, param):
        """
        Return the value of the configuration parameter *param*.  Raise
        exception if not found.
        """
        try:
            val = self.sim_conf[param]
        except KeyError:
            try:
                msg_id = self._invoke_service(self.fwk.component_id,
                                            'get_config_parameter', param)
                val = self._get_service_response(msg_id, block=True)
            except Exception:
                self.exception('Error retrieving value of config parameter %s' , param)
                raise
        return val

    def set_config_param(self, param, value, target_sim_name=None):
        """
        Set configuration parameter *param* to *value*.  Raise exceptions if
        the parameter cannot be changed or if there are problems setting the
        value.
        """
        if (target_sim_name == None):
            sim_name = self.sim_name
        else:
            sim_name = target_sim_name
        if (param in self.sim_conf.keys()):
            raise Exception('Cannot dynamically alter simulation configuration parameter ' + param)
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                        'set_config_parameter', param, value, sim_name)
            retval = self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error setting value of configuration parameter %s' , param)
            raise
        return retval

    def getGlobalConfigParameter(self, param):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.get_config_param`
        """
        self.warning('Method getGlobalConfigParameter() deprecated - use get_config_param() instead')
        return self.get_config_param(param)

    def getTimeLoop(self):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.get_time_loop`
        """
        self.warning('getTimeLoop() deprecated - use get_time_loop() instead')
        return self.get_time_loop()

    def get_time_loop(self):
        """
        Return the list of times as specified in the configuration file.
        """
        if (self.time_loop != None):
            return self.time_loop
        sim_conf = self.sim_conf
        tlist = []
        time_conf = sim_conf['TIME_LOOP']
        safe = lambda nums: len(set(str(nums)).difference(set("1234567890-+/*.e "))) == 0
        # generate tlist in regular mode (start, finish, step)
        if (time_conf['MODE'] == 'REGULAR'):
            for entry in ['FINISH', 'START', 'NSTEP']:
                if not safe(time_conf[entry]):
                    self.exception('Invalid TIME_LOOP value of %s = %s' % (entry, time_conf[entry]))
                    raise Exception('Invalid TIME_LOOP value of %s = %s' % (entry, time_conf[entry]))
            finish = float(eval(time_conf['FINISH']))
            start = float(eval(time_conf['START']))
            nstep = int(eval(time_conf['NSTEP']))
            step = (finish - start) / nstep
            tlist = [start + step * n for n in range(nstep+1)]
        # generate tlist in explicit mode (list of times)
        elif time_conf['MODE'] == 'EXPLICIT' :
            tlist = [float(v) for v in time_conf['VALUES'].split()]
        self.time_loop = tlist
        return tlist

    def checkpoint_components(self, comp_id_list, time_stamp, Force = False, Protect = False):
        """
        Selectively checkpoint components in *comp_id_list* based on the
        configuration section *CHECKPOINT*.  If *Force* is ``True``, the
        checkpoint will be taken even if the conditions for taking the
        checkpoint are not met.  If *Protect* is ``True``, then the data from
        the checkpoint is protected from clean up.  *Force* and *Protect* are
        optional and default to ``False``.

        The *CHECKPOINT_MODE* option controls determines if the components
        checkpoint methods are invoked.

        Possible *MODE* options are:

        ALL:
            Checkpint everytime the call is made (equivalent to always setting
            Force =True)
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
        """

        elapsed_time = self._get_elapsed_time()
        if (Force):
            return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
        try:
            chkpt_conf =  self.sim_conf['CHECKPOINT']
            mode = chkpt_conf['MODE']
            num_chkpt = int(chkpt_conf['NUM_CHECKPOINT'])
        except KeyError:
            self.error('Missing CHECKPOINT config section, or one of the required parameters: MODE, NUM_CHECKPOINT')
            self.exception('Error accessing CHECKPOINT section in config file')
            raise

        if (num_chkpt == 0):
            return

        if (mode not in ['ALL', 'WALLTIME_REGULAR',  'WALLTIME_EXPLICIT',
                         'PHYSTIME_REGULAR', 'PHYSTIME_EXPLICIT']):
            self.error('Invalid MODE = %s in checkpoint configuration', mode)
            raise Exception('Invalid MODE = %s in checkpoint configuration'% (mode))

        if (mode == 'ALL'):
            return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)

        if (mode == 'WALLTIME_REGULAR'):
            interval = float(chkpt_conf['WALLTIME_INTERVAL'])
            if (self.cur_time - self.last_ckpt_walltime >= interval):
                return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
            else:
                return None
        elif (mode == 'WALLTIME_EXPLICIT'):
            try:
                wt_values = chkpt_conf['WALLTIME_VALUES'].split()
            except AttributeError:
                wt_values = chkpt_conf['WALLTIME_VALUES']

            wt_values = [float(t) for t in wt_values]
            for t in wt_values:
                if ((elapsed_time >= t) and
                    (self.last_ckpt_walltime - self.start_time < t)):
                    return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
            return None
        elif (mode == 'PHYSTIME_REGULAR'):
            pt_interval = float(chkpt_conf['PHYSTIME_INTERVAL'])
            pt_current = float(time_stamp)
            pt_start = self.time_loop[0]
            if (self.last_ckpt_phystime == None):
                self.last_ckpt_phystime = pt_start
            if (pt_current - self.last_ckpt_phystime >= pt_interval):
                return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
            else:
                return None
        elif(mode == 'PHYSTIME_EXPLICIT'):
            #print ">>>>>>> chkpt_conf['PHYSTIME_VALUES'] = ", chkpt_conf['PHYSTIME_VALUES']
            try:
                pt_values = chkpt_conf['PHYSTIME_VALUES'].split()
            except AttributeError:
                pt_values = chkpt_conf['PHYSTIME_VALUES']
            pt_values = [float(t) for t in pt_values]
            #print ">>>>>>> pt_values = ", pt_values
            pt_current = float(time_stamp)
            for pt in pt_values:
                if (pt_current >= pt and
                    self.last_ckpt_phystime < pt):
                    return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
            return None
        return None

    def _dispatch_checkpoint(self, time_stamp, comp_id_list, Protect):
        """
        Invoke *checkpoint* method on each component in *comp_id_list* labeled
        with time *time_stamp*.  If *Protect* is ``True``, or this checkpoint
        is designated as a protected checkpoint by the simulation
        configuration parameters, steps are taken to ensure it remains in the
        restart directory.  Unprotected checkpoints are purged as necessary.
        """
        self.last_ckpt_walltime = self.cur_time
        self.last_ckpt_phystime = float(time_stamp)
        self.debug('Checkpointing components after %.3f sec with physics time = %.3f',
                   self.last_ckpt_walltime-self.start_time, self.last_ckpt_phystime)
        self._send_monitor_event('IPS_CHECKPOINT_START',
                                'Components = ' + str(comp_id_list))
        call_id_list = []
        for comp_id in comp_id_list:
            call_id = self.call_nonblocking(comp_id, 'checkpoint', time_stamp)
            call_id_list.append(call_id)
        ret_dict = self.wait_call_list(call_id_list, block=True)

        self.chkpt_counter += 1
        sim_root = self.sim_conf['SIM_ROOT']
        chkpt_conf = self.sim_conf['CHECKPOINT']

        num_chkpt = int(chkpt_conf['NUM_CHECKPOINT'])
        # num_chkpt < 0 mens keep all checkpoints
        # num_chkpt = 0 means no checkpoints
        if (num_chkpt <= 0):
            return ret_dict

        base_dir = os.path.join(sim_root, 'restart')
        timeStamp_str =  '%0.3f' % (float(time_stamp))
        self.new_chkpts.append(timeStamp_str)
        try:
            protect_freq = chkpt_conf['PROTECT_FREQUENCY']
        except KeyError:
            pass
        else:
            if (Protect or (self.chkpt_counter % int(protect_freq) == 0)):
                self.protected_chkpts.append(timeStamp_str)

        if (os.path.isdir(base_dir)):
            all_chkpts = [os.path.basename(f)  for f in glob.glob(os.path.join(base_dir,'*'))
                               if os.path.isdir(f)]
            prior_runs_chkpts_dirs = [chkpt for chkpt in all_chkpts if chkpt not in self.new_chkpts]
            purge_candidates = sorted(prior_runs_chkpts_dirs, key=float)
            purge_candidates += [chkpt for chkpt in self.new_chkpts if (chkpt in all_chkpts and
                           chkpt not in self.protected_chkpts)]
#            self.debug('CHECKPOINT: all_chkpts = %s', str(all_chkpts))
#            self.debug('CHECKPOINT: purge_candidates = %s', str(purge_candidates))
#            self.debug('CHECKPOINT: protected_chkpts = %s', str(self.protected_chkpts))
#            self.debug('CHECKPOINT: ***********************')
            while (len(purge_candidates) > num_chkpt):
                obsolete_chkpt = purge_candidates.pop(0)
                chkpt_dir = os.path.join(base_dir, obsolete_chkpt)
                try:
                    shutil.rmtree(chkpt_dir)
                except:
                    self.exception('Error removing directory %s', chkpt_dir)
                    raise
        self._send_monitor_event('IPS_CHECKPOINT_END',
                                'Components = ' + str(comp_id_list))
        return ret_dict

    # DM getWorkDir
    def get_working_dir(self):
        """
        Return the working directory of the calling component.

        The structure of the working directory is defined using the
        configuration parameters *CLASS*, *SUB_CLASS*, and *NAME* of the
        component configuration section. The structure
        of the working directory is::

            ${SIM_ROOT}/work/$CLASS_${SUB_CLASS}_$NAME_<instance_num>

        """
        if (self.workdir ==''):
            self.workdir = os.path.join(self.sim_conf['SIM_ROOT'], 'work',
                                        self.full_comp_id)
        return self.workdir

    # DM stageInput
    def stage_input_files_old(self, input_file_list):
        """
        Copy component input files to the component working directory
        (as obtained via a call to :py:meth:`ServicesProxy.get_working_dir`). Input files
        are assumed to be originally located in the directory variable
        *INPUT_DIR* in the component configuration section.
        """
        start_time = time.time()
        workdir = self.get_working_dir()
        conf = self.component_ref.config
        inputDir = conf['INPUT_DIR']
        ipsutil.copyFiles(inputDir, input_file_list, workdir)

        # Copy input files into a central place in the output tree
        simroot = self.sim_conf['SIM_ROOT']
        try:
            outprefix =  self.sim_conf['OUTPUT_PREFIX']
        except KeyError, e:
            outprefix=''

        targetdir = os.path.join(simroot , 'simulation_setup',
                                 self.full_comp_id)
        try:
            #print 'inputDir =', inputDir
            #print 'input_file_list =', input_file_list
            #print 'targetdir =', targetdir
            #print 'outprefix =', outprefix

            ipsutil.copyFiles(inputDir, input_file_list, targetdir, outprefix)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_INPUTS',
                                           'Files = ' + str(input_file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in stage_input_files')
            raise e
        elapsed_time = time.time() - start_time
        self._send_monitor_event(eventType='IPS_STAGE_INPUTS',
                                 comment='Elapsed time = %.3f Path = %s Files = %s' % \
                                         (elapsed_time, os.path.abspath(inputDir), \
                                          str(input_file_list)))

        return
    # DM stageInput
    def stage_input_files(self, input_file_list):
        """
        Copy component input files to the component working directory
        (as obtained via a call to :py:meth:`ServicesProxy.get_working_dir`). Input files
        are assumed to be originally located in the directory variable
        *INPUT_DIR* in the component configuration section.
        """
        start_time = time.time()
        workdir = self.get_working_dir()
        old_conf = self.component_ref.config
        inputDir = old_conf['INPUT_DIR']
        ipsutil.copyFiles(inputDir, input_file_list, workdir)

        # Copy input files into a central place in the output tree
        simroot = self.sim_conf['SIM_ROOT']
        try:
            outprefix =  self.sim_conf['OUTPUT_PREFIX']
        except KeyError, e:
            outprefix=''

        targetdir = os.path.join(simroot , 'simulation_setup',
                                 self.full_comp_id)
        try:
            #print 'inputDir =', inputDir
            #print 'input_file_list =', input_file_list
            #print 'targetdir =', targetdir
            #print 'outprefix =', outprefix

            ipsutil.copyFiles(inputDir, input_file_list, targetdir, outprefix)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_INPUTS',
                                           'Files = ' + str(input_file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in stage_input_files')
            raise e
        for (name, (new_conf, old_conf, init_comp, driver_comp)) in self.sub_flows.iteritems():
            ports = old_conf['PORTS']['NAMES'].split()
            comps = [old_conf['PORTS'][p]['IMPLEMENTATION'] for p in ports]
            for c in comps:
                input_dir = old_conf[c]['INPUT_DIR']
                input_files = old_conf[c]['INPUT_FILES']
                print '---- Staging inputs for %s:%s' %(name, c)
                input_target_dir = os.path.join(os.getcwd(), c)
                try:
                    os.mkdir(input_target_dir)
                except OSError, e:
                    if e.errno != 17:
                        raise
                try:
                    ipsutil.copyFiles(input_dir, input_files, input_target_dir)
                except Exception, e:
                    self._send_monitor_event('IPS_STAGE_INPUTS',
                                             'Files = ' + str(input_files) +
                                             ' Exception raised : ' + str(e),
                                             ok='False')
                    self.exception('Error in stage_input_files')
                    raise e
        elapsed_time = time.time() - start_time
        self._send_monitor_event(eventType='IPS_STAGE_INPUTS',
                                 comment='Elapsed time = %.3f Path = %s Files = %s' % \
                                         (elapsed_time, os.path.abspath(inputDir), \
                                          str(input_file_list)))

        return

    def stageInputFiles(self, input_file_list):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.stage_input_files`
        """
        self.warning('stageInputFiles() deprecated - use stage_input_files() instead')
        return self.stage_input_files(input_file_list)

    # SIMYAN: added method to specifically enable components to stage
    # data files to the component working directory
    def stage_data_files(self, data_file_list):
        """
        Copy component data files to the component working directory
        (as obtained via a call to :py:meth:`ServicesProxy.get_working_dir`). Input files
        are assumed to be originally located in the directory variable
        *DATA_TREE_ROOT* in the component configuration section.
        """
        workdir = self.get_working_dir()
        conf = self.component_ref.config
        dataDir = conf['DATA_DIR']
        ipsutil.copyFiles(dataDir, data_file_list, workdir)

        # Copy input files into a central place in the output tree
        simroot = self.sim_conf['SIM_ROOT']
        try:
            outprefix =  self.sim_conf['OUTPUT_PREFIX']
        except KeyError, e:
            outprefix=''

        targetdir = os.path.join(simroot , 'simulation_setup',
                                 self.full_comp_id)
        try:
            ipsutil.copyFiles(dataDir, data_file_list, targetdir, outprefix)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_DATA',
                                           'Files = ' + str(data_file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in stage_data_files')
            raise e
        self._send_monitor_event('IPS_STAGE_DATA','Files = '+str(data_file_list))

        return


    def stage_nonPS_output_files(self, timeStamp, file_list, keep_old_files = True):
        """
        Same as stage_output_files, but does not do anything with the Plasma State.
        """
        workdir = self.get_working_dir()
        conf = self.component_ref.config
        sim_root = self.sim_conf['SIM_ROOT']
        try:
            outprefix = self.sim_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''
        out_root = 'simulation_results'

        output_dir = os.path.join(sim_root, out_root, \
                                 str(timeStamp), 'components' ,
                                 self.full_comp_id)
        try:
            ipsutil.copyFiles(workdir, file_list, output_dir, outprefix,
                              keep_old=keep_old_files)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                           'Files = ' + str(file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in stage_nonPS_output_files()')
            raise

        # Store symlinks to component output files in a single top-level directory

        symlink_dir =  os.path.join(sim_root, out_root, self.full_comp_id)
        try:
            os.makedirs(symlink_dir)
        except OSError, e:
            if (e.errno != 17):
                self.exception('Error creating directory %s : %s' ,
                               symlink_dir, e.strerror)
                raise

        all_files = sum([glob.glob(f) for f in file_list.split()], [])

        for f in all_files:
            real_file = os.path.join(output_dir, outprefix + f)
            tokens = f.rsplit('.', 1)
            if (len(tokens) == 1) :
                newName = '_'.join([f , str(timeStamp)])
            else:
                name = tokens[0]
                ext = tokens[1]
                newName = '_'.join([name, str(timeStamp)]) + '.' + ext
            sym_link = os.path.join(symlink_dir, newName)
            if os.path.isfile(sym_link):
                os.remove(sym_link)
            # We need to use relative path for the symlinks
            common1 = os.path.commonprefix([real_file, sym_link])
            (head, sep, tail)= common1.rpartition('/')
            common = head.split('/')
            file_suffix = real_file.split('/')[len(common):] # Include file name
            link_suffix = sym_link.split('/')[len(common):-1] # No file name
            p = []
            if len(link_suffix) > 0:
                p = [ '../' * len(link_suffix) ]
            p = p + file_suffix
            relpath = os.path.join( *p )
            os.symlink(relpath, sym_link)

        self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                 'Files = ' + str(file_list))
        return

    def stage_PS_output_files(self, timeStamp, file_list, keep_old_files = True):
        """
        Same as stage_output_files, but only does Plasma State files.
        """
        workdir = self.get_working_dir()
        conf = self.component_ref.config
        sim_root = self.sim_conf['SIM_ROOT']
        try:
            outprefix = self.sim_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''
        out_root = 'simulation_results'

        output_dir = os.path.join(sim_root, out_root, \
                                 str(timeStamp), 'components' ,
                                 self.full_comp_id)

        # Store plasma state files into $SIM_ROOT/history/plasma_state
        # Plasma state files are renamed, by appending the full component
        # name (CLASS_SUBCLASS_NAME) and timestamp to the file name.
        # A version number is added to the end of the file name to avoid
        # overwriting existing plasma state files
        plasma_dir = os.path.join(self.sim_conf['SIM_ROOT'],
                                 'simulation_results',
                                 'plasma_state')
        try:
            os.makedirs(plasma_dir)
        except OSError, e:
            if (e.errno != 17):
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                         'Files = ' + str(file_list) + \
                                         ' Exception raised : ' + e.strerror,
                                         ok='False')
                self.exception('Error creating directory %s : %d-%s',
                               plasma_dir, e.errno, e.strerror)
                raise

        try:
            plasma_state_files = conf['PLASMA_STATE_FILES'].split()
        except KeyError:
            plasma_state_files = self.get_config_param('PLASMA_STATE_FILES').split()

        all_plasma_files=[]
        for plasma_file in plasma_state_files:
            globbed_files = glob.glob(plasma_file)
            if (len(globbed_files) > 0):
                all_plasma_files += globbed_files

        for f in all_plasma_files:
            if not os.path.isfile(f):
                continue
            tokens = f.split('.')
            if (len(tokens) == 1) :
                newName = '_'.join([outprefix + f , self.full_comp_id , str(timeStamp)])
            else:
                name = '.'.join(tokens[:-1])
                ext = tokens[-1]
                newName = '_'.join([outprefix + name, self.full_comp_id, str(timeStamp)]) + \
                           '.' + ext
            target_name = os.path.join(plasma_dir, newName)
            if os.path.isfile(target_name):
                for i in range(1000):
                    newName = target_name + '.' + str(i)
                    if  os.path.isfile(newName):
                        continue
                    target_name = newName
                    break
            try:
                shutil.copy(f, target_name)
            except (IOError, os.error), why:
                self.exception('Error copying file: %s from %s to %s - %s' ,
                               f, workdir, target_name, str(why))
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                     'Files = ' + str(file_list) + \
                                     ' Exception raised : ' + str(why),
                                     ok='False')
                raise

        self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                 'Files = ' + str(file_list))
        return

    def stage_subflow_output_files(self):
        # Gather outputs from any sub-workflows. Sub-workflow output
        # is defined to be the output files from its DRIVER component
        # as they exist in the sub-workflow driver's work area at the
        # end of the sub-simulation

        for (sim_name, (sub_conf_new, _, _, driver_comp)) in self.sub_flows.iteritems():
            ports = sub_conf_new['PORTS']['NAMES'].split()
            driver = sub_conf_new[sub_conf_new['PORTS']['DRIVER']['IMPLEMENTATION']]
            output_dir = os.path.join(sub_conf_new['SIM_ROOT'], 'work',
                                      '_'.join([driver['CLASS'], driver['SUB_CLASS'],
                                       driver['NAME'],
                                       str(driver_comp.get_seq_num())]))
            #print '################',  output_dir
            output_files = driver['OUTPUT_FILES']
            try:
                ipsutil.copyFiles(output_dir, output_files, self.get_working_dir(), keep_old=False)
            except Exception, e:
                self._send_monitor_event('IPS_STAGE_SUBFLOW_OUTPUTS',
                                           'Files = ' + str(output_files) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
                self.exception('Error in stage_subflow_output_files()')
                raise
        return



    def stage_output_files(self, timeStamp, file_list, keep_old_files = True):
        """
        Copy associated component output files (from the working directory)
        to the component simulation results directory. Output files
        are prefixed with the configuration parameter *OUTPUT_PREFIX*.
        The simulation results directory has the format::

            ${SIM_ROOT}/simulation_results/<timeStamp>/components/$CLASS_${SUB_CLASS}_$NAME_${SEQ_NUM}

        Additionally, plasma state files are archived for debugging purposes::

            ${SIM_ROOT}/history/plasma_state/<file_name>_$CLASS_${SUB_CLASS}_$NAME_<timeStamp>

        Copying errors are not fatal (exception raised).
        """
        start_time = time.time()
        workdir = self.get_working_dir()
        conf = self.component_ref.config
        sim_root = self.sim_conf['SIM_ROOT']
        try:
            outprefix = self.sim_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''
        out_root = 'simulation_results'

        output_dir = os.path.join(sim_root, out_root, \
                                 str(timeStamp), 'components' ,
                                 self.full_comp_id)
        if (type(file_list).__name__ == 'str'):
            file_list = file_list.split()
        all_files = sum([glob.glob(f) for f in file_list], [])
        try:
            ipsutil.copyFiles(workdir, all_files, output_dir, outprefix,
                              keep_old=keep_old_files)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                           'Files = ' + str(file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in stage_output_files()')
            raise

        # Store plasma state files into $SIM_ROOT/history/plasma_state
        # Plasma state files are renamed, by appending the full component
        # name (CLASS_SUBCLASS_NAME) and timestamp to the file name.
        # A version number is added to the end of the file name to avoid
        # overwriting existing plasma state files
        plasma_dir = os.path.join(self.sim_conf['SIM_ROOT'],
                                 'simulation_results',
                                 'plasma_state')
        try:
            os.makedirs(plasma_dir)
        except OSError, e:
            if (e.errno != 17):
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                         'Files = ' + str(file_list) + \
                                         ' Exception raised : ' + e.strerror,
                                         ok='False')
                self.exception('Error creating directory %s : %d-%s',
                               plasma_dir, e.errno, e.strerror)
                raise

        try:
            plasma_state_files = conf['PLASMA_STATE_FILES'].split()
        except KeyError:
            plasma_state_files = self.get_config_param('PLASMA_STATE_FILES').split()

        all_plasma_files=[]
        for plasma_file in plasma_state_files:
            globbed_files = glob.glob(plasma_file)
            if (len(globbed_files) > 0):
                all_plasma_files += globbed_files

        for f in all_plasma_files:
            if not os.path.isfile(f):
                continue
            tokens = f.split('.')
            if (len(tokens) == 1) :
                newName = '_'.join([outprefix + f , self.full_comp_id , str(timeStamp)])
            else:
                name = '.'.join(tokens[:-1])
                ext = tokens[-1]
                newName = '_'.join([outprefix + name, self.full_comp_id, str(timeStamp)]) + \
                           '.' + ext
            target_name = os.path.join(plasma_dir, newName)
            if os.path.isfile(target_name):
                for i in range(1000):
                    newName = target_name + '.' + str(i)
                    if  os.path.isfile(newName):
                        continue
                    target_name = newName
                    break
            try:
                shutil.copy(f, target_name)
            except (IOError, os.error), why:
                self.exception('Error copying file: %s from %s to %s - %s' ,
                               f, workdir, target_name, str(why))
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                     'Files = ' + str(file_list) + \
                                     ' Exception raised : ' + str(why),
                                     ok='False')
                raise

        # Store symlinks to component output files in a single top-level directory

        symlink_dir =  os.path.join(sim_root, out_root, self.full_comp_id)
        try:
            os.makedirs(symlink_dir)
        except OSError, e:
            if (e.errno != 17):
                self.exception('Error creating directory %s : %s' ,
                               symlink_dir, e.strerror)
                raise

        all_files = sum([glob.glob(f) for f in file_list], [])

        for f in all_files:
            real_file = os.path.join(output_dir, outprefix + f)
            tokens = f.rsplit('.', 1)
            if (len(tokens) == 1) :
                newName = '_'.join([f , str(timeStamp)])
            else:
                name = tokens[0]
                ext = tokens[1]
                newName = '_'.join([name, str(timeStamp)]) + '.' + ext
            sym_link = os.path.join(symlink_dir, newName)
            if os.path.isfile(sym_link):
                os.remove(sym_link)
            # We need to use relative path for the symlinks
            common1 = os.path.commonprefix([real_file, sym_link])
            (head, sep, tail)= common1.rpartition('/')
            common = head.split('/')
            file_suffix = real_file.split('/')[len(common):] # Include file name
            link_suffix = sym_link.split('/')[len(common):-1] # No file name
            p = []
            if len(link_suffix) > 0:
                p = [ '../' * len(link_suffix) ]
            p = p + file_suffix
            relpath = os.path.join( *p )
            os.symlink(relpath, sym_link)

        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                 'Elapsed time = %.3f Path = %s Files = %s' % \
                                  (elapsed_time, output_dir, str(file_list)))
        return

    def stageOutputFiles(self, timeStamp, output_file_list):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.stage_output_files`
        """
        self.warning('stageOutputFiles() deprecated - use stage_output_files() instead')
        return self.stage_output_files(timeStamp, output_file_list)

    def save_restart_files(self, timeStamp, file_list):
        """
        Copy files needed for component restart to the restart directory::

            ${SIM_ROOT}/restart/$timestamp/components/$CLASS_${SUB_CLASS}_$NAME

        Copying errors are not fatal (exception raised).
        """
        workdir = self.get_working_dir()
        sim_root = self.sim_conf['SIM_ROOT']
        chkpt_conf = self.sim_conf['CHECKPOINT']

        num_chkpt = int(chkpt_conf['NUM_CHECKPOINT'])
        # num_chkpt < 0 mens keep all checkpoints
        # num_chkpt = 0 means no checkpoints
        if (num_chkpt == 0):
            return
        conf = self.component_ref.config
        base_dir = os.path.join(sim_root, 'restart')
        timeStamp_str =  '%0.3f' % (float(timeStamp))
        self.new_chkpts.append(timeStamp_str)

        targetdir = os.path.join(base_dir,
                                 timeStamp_str,
                                 '_'.join([conf['CLASS'],
                                           conf['SUB_CLASS'],
                                           conf['NAME']]))
        self.debug('Checkpointing: Copying %s to dir %s', str(file_list), targetdir)

        try:
            ipsutil.copyFiles(workdir, file_list, targetdir)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_RESTART',
                                           'Files = ' + str(file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in stage_restart_files()')
            raise

        self._send_monitor_event('IPS_SAVE_RESTART',
                                 'Files = ' + str(file_list))
        return

    def get_restart_files(self, restart_root, timeStamp, file_list):
        """
        Copy files needed for component restart from the restart directory::

            <restart_root>/restart/<timeStamp>/components/$CLASS_${SUB_CLASS}_$NAME_${SEQ_NUM}

        to the component's work directory.

        Copying errors are not fatal (exception raised).
        """
        work_dir = self.get_working_dir()

        conf = self.component_ref.config
        base_dir = os.path.join(restart_root, 'restart',
                                    '%.3f' % (float(timeStamp)))
        source_dir = os.path.join(base_dir,
                                  '_'.join([conf['CLASS'],
                                           conf['SUB_CLASS'],
                                           conf['NAME']]))

        try:
            ipsutil.copyFiles(source_dir, file_list, work_dir)
        except Exception, e:
            self._send_monitor_event('IPS_GET_RESTART',
                                           'Files = ' + str(file_list) + \
                                           ' Exception raised : ' + str(e),
                                           ok='False')
            self.exception('Error in get_restart_files()')
            raise

        self._send_monitor_event('IPS_GET_RESTART',
                                 'Files = ' + str(file_list))
        return

    def stage_plasma_state(self):
        """
        Copy current plasma state to work directory.
        """
        start_time = time.time()
        conf = self.component_ref.config
        try:
            files = conf['PLASMA_STATE_FILES'].split()
        except KeyError:
            files = self.get_config_param('PLASMA_STATE_FILES').split()

        state_dir = self.get_config_param('PLASMA_STATE_WORK_DIR')
        workdir = self.get_working_dir()
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'stage_plasma_state', files, state_dir, workdir)
            retval = self._get_service_response(msg_id, block=True)
        except Exception, e:
            self._send_monitor_event('IPS_STAGE_PLASMA_STATE',
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error staging plasma state files')
            raise
        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_STAGE_PLASMA_STATE',
                                 'Elapsed time = %.3f  files = %s Success' %\
                                 (elapsed_time, ' '.join(files)))
        return

    def stageCurrentPlasmaState(self):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.stage_plasma_state`
        """
        self.warning('stageCurrentPlasmaState() deprecated - use stage_plasma_state() instead')
        return self.stage_plasma_state()

    def update_plasma_state(self, plasma_state_files = None):
        """
        Copy local (updated) plasma state to global state.  If no plasma state
        files are specified, component configuration specification is used.
        Raise exceptions upon copy.
        """
        start_time = time.time()
        conf = self.component_ref.config
        if not plasma_state_files:
            try:
                files = conf['PLASMA_STATE_FILES'].split()
            except KeyError:
                files = self.get_config_param('PLASMA_STATE_FILES').split()
        else:
            files = ' '.join(plasma_state_files).split()

        state_dir = self.get_config_param('PLASMA_STATE_WORK_DIR')
        workdir = self.get_working_dir()
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'update_plasma_state', files, workdir, state_dir)
            retval = self._get_service_response(msg_id, block=True)
        except Exception, e:
            print 'Error updating plasma state files', str(e)
            self._send_monitor_event('IPS_UPDATE_PLASMA_STATE',
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error updating plasma state files')
            raise
        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_UPDATE_PLASMA_STATE',
                                 'Elapsed time = %.3f   files = %s Success' % \
                                  (elapsed_time, ' '.join(files)))
        return

    def merge_current_plasma_state(self, partial_state_file, logfile=None):
        """
        Merge partial plasma state with global state.  Partial plasma state
        contains only the values that the component contributes to the
        simulation.  Raise exceptions on bad merge.  Optional *logfile* will
        capture ``stdout`` from merge.
        """
        state_dir = self.get_config_param('PLASMA_STATE_WORK_DIR')
        current_plasma_state = self.get_config_param('CURRENT_STATE')
        workdir = self.get_working_dir()
        if (os.path.isabs(partial_state_file)):
            update_file = partial_state_file
        else:
            update_file = os.path.join(workdir, partial_state_file)
        source_plasma_file = os.path.join(state_dir, current_plasma_state)
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                            'merge_current_plasma_state', update_file,
                            source_plasma_file, logfile)
            retval = self._get_service_response(msg_id, block=True)
        except Exception, e:
            print 'Error merging plasma state files', str(e)
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE',
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error merging plasma state file '+ partial_state_file)
            raise
        if (retval == 0):
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE',
                                 'Success')
            return
        else:
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE',
                                     ' Error in call to update_state() : ',
                                     ok='False')
            self.error('Error merging update %s into current plasma state file %s',
                       partial_state_file, current_plasma_state)
            raise Exception('Error merging update %s into current plasma state file %s'%
                       (partial_state_file, current_plasma_state))

    def updatePlasmaState(self):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.update_plasma_state`
        """
        self.warning('updatePlasmaState() deprecated - use update_plasma_state() instead')
        return self.update_plasma_state()

    def updateTimeStamp(self, newTimeStamp = -1):
        """
        .. deprecated :: 1.0 Use :py:meth:`ServicesProxy.update_time_stamp`
        """
        self.warning('updateTimeStamp() deprecated - use update_time_stamp() instead')
        self.update_time_stamp(newTimeStamp)

    def update_time_stamp(self, new_time_stamp = -1):
        """
        Update time stamp on portal.
        """
        event_data = {}
        event_data['sim_name'] = self.sim_name
        portal_data={}
        portal_data['phystimestamp'] = new_time_stamp
        portal_data['eventtype'] = 'PORTALBRIDGE_UPDATE_TIMESTAMP'
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTALBRIDGE_UPDATE_TIMESTAMP', event_data)
        self._send_monitor_event('IPS_UPDATE_TIME_STAMP', 'Timestamp = ' + str(new_time_stamp))
        return

    def _get_replay_comp_data(self, timeStamp):
        """
        Return data files from replay component at time *timeStamp*.
        """
        try:
            replay_sim_root = self.component_ref.REPLAY_SIM_ROOT
            replay_port = self.component_ref.REPLAY_PORT
            replay_config_file = self.component_ref.REPLAY_CONFIG_FILE
        except:
            self.exception('Error retrieving replay configuration parameters')
            raise
        if not self.replay_conf:
            try:
                self.replay_conf=ConfigObj(replay_config_file, interpolation='template',
                                 file_error=True)
            except IOError:
                self.exception('Error opening config file: %s', replay_config_file)
                raise
        ports = self.replay_conf['PORTS']
        comp_conf = None
        try:
            comp_conf = ports[replay_port]['IMPLEMENTATION']
        except:
            self.exception('Error accessing replay component for port %s',
                           replay_port)
            raise
        output_files = comp_conf['OUTPUT_FILES'].split()
        try:
            outprefix = comp_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''
        out_root = 'simulation_results'
        comp_id_prefix = '_'.join([comp_conf['CLASS'],
                                    comp_conf['SUB_CLASS'],
                                    comp_conf['NAME']])
        out_path = os.path.join(replay_sim_root, out_root)
        comp_dirs = glob.glob(os.path.join(out_path, comp_id_prefix + '_*'))
        if (len(comp_dirs) != 1):
            self.error('Could not find a single component instance implementing port %s',
                       replay_port)
            raise Exception('Could not find a single component instance implementing port %s ' +
                       replay_port)
        replay_comp_id = os.path.basename(comp_dirs[0])
        plasma_files = []
        try:
            plasma_files = comp_conf['PLASMA_STATE_FILES'].split()
        except KeyError:
            plasma_files = self.replay_conf['PLASMA_STATE_FILES'].split()

        return (comp_conf,
                outprefix,
                replay_sim_root,
                replay_comp_id,
                output_files,
                plasma_files)

    def stage_replay_output_files(self, timeStamp):
        """
        Copy output files from the replay component to current sim for
        physics time *timeStamp*.  Return location of new local copies.
        """
        replay_comp_data = self._get_replay_comp_data(timeStamp)
        comp_conf = replay_comp_data[0]
        outprefix = replay_comp_data[1]
        replay_sim_root = replay_comp_data[2]
        replay_comp_id = replay_comp_data[3]
        output_files = replay_comp_data[4]

        symlink_dir  = os.path.join(replay_sim_root, 'simulation_results', replay_comp_id)
        prefix_out_files = [outprefix+f for f in output_files]
        local_output_files=[]
        use_sym_link = False
        try:
            use_sym_link = self.component_ref.config['USE_SYM_LINK']
        except KeyError:
            pass
        for f in prefix_out_files:
            tokens = f.rsplit('.', 1)
            if (len(tokens) == 1) :
                link_name = '_'.join([f , str(timeStamp)])
            else:
                name = tokens[0]
                ext = tokens[1]
                link_name = '_'.join([name, str(timeStamp)]) + '.' + ext
            sym_link = os.path.join(symlink_dir, link_name)
            try:
                if (use_sym_link):
                    try:
                        os.symlink(sym_link, f)
                    except Exception:
                        shutil.copy(sym_link, f)
                else:
                    shutil.copy(sym_link, f)
            except:
                self.exception('Error copying replay file from %s to %s',
                               sym_link, f)
                raise
            local_output_files.append(f)
        self._send_monitor_event('IPS_STAGE_REPLAY_OUTPUT_FILES',
                                 'Files = ' + str(output_files))
        return local_output_files

    def stage_replay_plasma_files(self, timeStamp):
        """
        Copy plasma state files from the replay component to current sim for
        physics time *timeStamp*.  Return location of new local copies.
        """
        replay_comp_data = self._get_replay_comp_data(timeStamp)
#        comp_conf = replay_comp_data[0]
        outprefix = replay_comp_data[1]
        replay_sim_root = replay_comp_data[2]
        replay_comp_id = replay_comp_data[3]
#        output_files = replay_comp_data[4]
        replay_plasma_files = replay_comp_data[5]

        plasma_dir = os.path.join(replay_sim_root,
                                  'simulation_results',
                                  'plasma_state')
        local_plasma_files = []
        use_sym_link = False
        try:
            use_sym_link = self.component_ref.config['USE_SYM_LINK']
        except KeyError:
            pass
        for f in replay_plasma_files:
            # Find config macro for the current file
            macro_name = None
            for (key, value) in self.replay_conf.iteritems():
                if (f == value):
                    macro_name = key
            if not macro_name:
                raise Exception('Unable to deduce macro name for file %s ' + f)
            target_name = self.get_config_param(macro_name)

            # Get name of replay file with embedded outprefix and timestamp
            tokens = f.split('.')
            if (len(tokens) == 1) :
                replay_fname = '_'.join([outprefix + f , replay_comp_id , str(timeStamp)])
            else:
                name = '.'.join(tokens[:-1])
                ext = tokens[-1]
                replay_fname = '_'.join([outprefix + name, replay_comp_id, str(timeStamp)]) + \
                           '.' + ext
            replay_file = os.path.join(plasma_dir, replay_fname)

            # Find the last file generated from this timestamp
            if not os.path.isfile(replay_file):
                raise Exception('Missing plasma state file %s' + replay_file)

            tmp = None
            for i in range(1000):
                if  os.path.isfile(replay_file + '.' + str(i)):
                    tmp = replay_file + '.' + str(i)
                    continue
                break
            if (tmp):
                replay_file = tmp

            try:
                if (use_sym_link):
                    try:
                        os.symlink(replay_file, target_name)
                    except Exception:
                        self.exception('Error creating symlink %s to %s',
                               target_name, replay_file)
                        shutil.copy(replay_file, target_name)
                else:
                    shutil.copy(replay_file, target_name)
            except:
                self.exception('Error copying replay file from %s to %s',
                               replay_file, target_name)
                self._send_monitor_event('IPS_STAGE_REPLAY_PLASMA_STATE',
                                     'Files = ' + str(replay_plasma_files) + \
                                     ' Exception raised : ',
                                     ok='False')
                raise
            local_plasma_files.append(replay_file)

        self._send_monitor_event('IPS_STAGE_REPLAY_PLASMA_STATE',
                                 'Files = ' + str(replay_plasma_files))
        return local_plasma_files

    def setMonitorURL(self, url=''):
        """
        Send event to portal setting the URL where the monitor component will
        put data.
        """
        self.monitor_url = url
        self._send_monitor_event(eventType = 'IPS_SET_MONITOR_URL', comment = 'SUCCESS')
        return

    def publish(self,topicName,eventName,eventBody):
        """
        Publish event consisting of *eventName* and *eventBody* to topic *topicName* to the IPS event service.
        """
        if not topicName.startswith('_IPS'):
            topicName = self.sim_name + '_' + topicName
        self.event_service.publish(topicName, eventName, eventBody)

    def subscribe(self, topicName, callback):
        """
        Subscribe to topic *topicName* on the IPS event service and register *callback* as the method to be invoked whem an event is published to that topic.
        """
        if not topicName.startswith('_IPS'):
            topicName = self.sim_name + '_' + topicName
        self.event_service.subscribe(topicName, callback)

    def unsubscribe(self, topicName):
        """
        Remove subscription to topic *topicName*.
        """
        if not topicName.startswith('_IPS'):
            topicName = self.sim_name + '_' + topicName
        self.event_service.unsubscribe(topicName)

    def process_events(self):
        """
        Poll for events on subscribed topics.
        """
        self.event_service.process_events()


    def send_portal_event(self,
                          event_type="COMPONENT_EVENT",
                          event_comment=""):
        """
        Send event to web portal.
        """
        return self._send_monitor_event(eventType = event_type,
                                        comment = event_comment)

    def log(self, *args):
        """
        Wrapper for :py:meth:`ServicesProxy.info`.
        """
        return self.info(args)


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
            self.error('Bad format in call to services.debug() ' + str(args))

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
            self.error('Bad format in call to services.info() ' + str(args))

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
            self.error('Bad format in call to services.warning() ' + str(args))

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
            self.error('Bad format in call to services.error() ' + str(args))

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
            self.error('Bad format in call to services.exception() ' + str(args))

    def critical(self, *args):
        """
        Produce **critical** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if (len(args) > 1):
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.critical(msg)
        except:
            self.error('Bad format in call to services.critical() ' + str(args))

    def create_task_pool(self, task_pool_name):
        """
        Create an empty pool of tasks with the name *task_pool_name*.  Raise exception if duplicate name.
        """
        if task_pool_name in self.task_pools.keys():
            raise Exception('Error: Duplicate task pool name %s' %(task_pool_name))
        self.task_pools[task_pool_name]= TaskPool(task_pool_name, self)
        return

    def add_task(self, task_pool_name, task_name, nproc, working_dir,
                 binary, *args, **keywords):
        """
        Add task *task_name* to task pool *task_pool_name*.  Remaining arguments are the same as in :py:meth:`ServicesProxy.launch_task`.
        """
        task_pool = self.task_pools[task_pool_name]
        return task_pool.add_task(task_name, nproc, working_dir, binary,
                                  *args, **keywords)

    def submit_tasks(self, task_pool_name, block=True):
        """
        Launch all unfinished tasks in task pool *task_pool_name*.  If *block* is ``True``, return when all tasks have been launched.  If *block* is ``False``, return when all tasks that can be launched immediately have been launched.  Return number of tasks submitted.
        """
        start_time = time.time()
        self._send_monitor_event('IPS_TASK_POOL_BEGIN', 'task_pool = %s ' % (task_pool_name))
        task_pool = self.task_pools[task_pool_name]
        retval = task_pool.submit_tasks(block)
        self._send_monitor_event('IPS_TASK_POOL_END', 'task_pool = %s  elapsed time = %.2f S' %
                                 (task_pool_name, time.time() - start_time))
        return retval

    def get_finished_tasks(self, task_pool_name):
        """
        Return dictionary of finished tasks and return values in task pool *task_pool_name*.  Raise exception if no active or finished tasks.
        """
        task_pool = self.task_pools[task_pool_name]
        return task_pool.get_finished_tasks_status()

    def remove_task_pool(self, task_pool_name):
        """
        Kill all running tasks, clean up all finished tasks, and delete task pool.
        """
        task_pool = self.task_pools[task_pool_name]
        task_pool.terminate_tasks()
        del self.task_pools[task_pool_name]
        return

    def create_sub_workflow(self, sub_name, config_file, override= None):

        if not override:
            override = {}
        if sub_name in self.sub_flows.keys():
            self.exception("Duplicate sub flow name")
            raise Exception("Duplicate sub flow name")

        print "Creating worflow using ", config_file
        self.subflow_count += 1
        try:
            sub_conf_new = ConfigObj(infile=config_file, interpolation='template', file_error=True)
            sub_conf_old = ConfigObj(infile=config_file, interpolation='template', file_error=True)
        except Exception:
            self.exception("Error accessing sub-workflow config file %s" % config_file)
            raise
        # Update undefined sub workflow configuration entries using top level configuration
        # only applicable to non-component entries (ones with non-dictionary values)
        for (k,v) in self.sim_conf.iteritems():
            if k not in sub_conf_new.keys() and type(v).__name__ != 'dict':
                sub_conf_new[k] = v

        sub_conf_new['SIM_ROOT'] = os.path.join(os.getcwd(), 'sub_workflow_%d' % self.subflow_count)
        # Update INPUT_DIR for components to current working dir (super simulation working dir)
        ports = sub_conf_new['PORTS']['NAMES'].split()
        comps = [sub_conf_new['PORTS'][p]['IMPLEMENTATION'] for p in ports]
        for c in comps:
            sub_conf_new[c]['INPUT_DIR'] = os.path.join(os.getcwd(), c)
            try:
                override_vals = override[c]
            except KeyError:
                pass
            else:
                for (k,v) in override_vals.iteritems():
                    sub_conf_new[c][k] = v
        toplevel_override = set(override.keys()) - set(comps)
        for param in toplevel_override:
            sub_conf_new[param] = override[param]

        sub_conf_new.filename = os.path.basename(config_file)
        sub_conf_new.write()
        try:
            (sim_name, init_comp, driver_comp) = self._create_simulation(os.path.abspath(sub_conf_new.filename),
                                                                         {}, sub_workflow=True)
        except Exception:
            raise
        self.sub_flows[sub_name] = (sub_conf_new, sub_conf_old, init_comp, driver_comp)
        self._send_monitor_event('IPS_CREATE_SUB_WORKFLOW', 'workflow_name = %s' % sub_name)
        return (sim_name, init_comp, driver_comp)


    def create_simulation(self, config_file, override):
        return self._create_simulation(config_file, override, sub_workflow=False)[0]

    def _create_simulation(self, config_file, override, sub_workflow=False):
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                        'create_simulation', config_file, override, sub_workflow)
            self.debug('create_simulation() msg_id = %s', msg_id)
            (sim_name, init_comp, driver_comp) = self._get_service_response(msg_id, block=True)
            self.debug('Created simulation %s', sim_name)
        except Exception:
            self.exception('Error creating new simulation')
            raise
        return (sim_name, init_comp, driver_comp)

class TaskPool(object):
    """
    Class to contain and manage a pool of tasks.
    """
    def __init__(self, name, services):
        self.name = name
        self.services = services
        self.active_tasks = {}
        self.finished_tasks = {}
        self.queued_tasks = {}
        self.blocked_tasks = {}

    def _wait_any_task(self, block = True):
        """
        Check the status of all tasks in *active_tasks*, finishing them as
        needed, and returning when at least one of them has finished.  If
        *block* is ``False``, returns after one traversal of *active_tasks*
        even if none of the tasks have finished.  If *block* is ``True``
        (default), returns only after at least one task has finished.  In this
        case, *active_tasks* may be traversed multiple times, sleeping for
        0.05 seconds between traversals.
        """
        if len(self.active_tasks) == 0:
            return
        done = False
        while not done:
            for task_id in self.active_tasks.keys():
                exit_status = self.services.wait_task_nonblocking(task_id)
                if (exit_status != None):
                    task = self.active_tasks.pop(task_id)
                    task.exit_status = exit_status
                    self.finished_tasks[task.name] = task
                    done = True
            if not done:
                if block:
                    time.sleep(0.05)
                else:
                    break
        return

    def _wait_active_tasks(self):
        """
        Call :py:meth:`TaskPool._wait_any_task` until there are no more *active_tasks*.
        """
        while (len(self.active_tasks) > 0):
            self._wait_any_task()
        pass

    def add_task(self, task_name, nproc, working_dir, binary, *args, **keywords):
        """
        Create :py:obj:`Task` object and add to *queued_tasks* of the task
        pool.  Raise exception if task name already exists in task pool.
        """
        tokens = binary.split()
        if len(tokens) > 1 :
            binary = tokens[0]
            args = tuple(tokens[1:]) + args
        try:
            binary_fullpath = self.services.binary_fullpath_cache[binary]
        except KeyError:        
            binary_fullpath = ipsutil.which(binary)
        if not binary_fullpath:
            self.services.error("Program %s is not in path or is not executable" % binary)
            raise Exception("Program %s is not in path or is not executable" % binary)
        else:
            self.services.binary_fullpath_cache[binary] = binary_fullpath

        if (task_name in self.queued_tasks):
            raise Exception('Duplicate task name %s in task pool' % (task_name))
        keywords['block'] = False

        self.queued_tasks[task_name] = Task(task_name, nproc, working_dir, binary_fullpath, *args, **keywords)
        return

    def submit_tasks(self, block = True):
        """
        Launch tasks in *queued_tasks*.  Finished tasks are handled before
        launching new ones.  If *block* is ``True``, the number of tasks
        submited is returned after all tasks have been launched and
        completed.  If *block* is ``False`` the number of tasks that can
        immediately be launched is returned.
        """
        submit_count = 0
        # Make sure any finished tasks are handled before attempting to submit
        # new ones
        self._wait_any_task(block = False)
        while True:
            if (len(self.queued_tasks) == 0):
                break
            active_tasks = self.services.launch_task_pool(self.name)
            for task_name, task_id in active_tasks.iteritems():
                self.active_tasks[task_id] = self.queued_tasks.pop(task_name)
                submit_count += 1
            if (block):
                self._wait_any_task()
                continue
            else:
                return submit_count
        if block:
            self._wait_active_tasks()
        return submit_count


    def submit_tasks_old(self, block = True):
        """
        .. deprecated :: Experimental Use :py:meth:`TaskPool.submit_tasks`
        """
        submit_count = 0
        while True:
            try:
                (task_name, task) = self.queued_tasks.popitem()
            except KeyError:
                if (len(self.blocked_tasks) == 0):
                    break
                else:
                    self.queued_tasks = self.blocked_tasks
                    self.blocked_tasks = {}
                    if (block):
                        self._wait_any_task()
                        continue
                    else:
                        return submit_count

            self.services.debug('Attempting to launch task %s', task_name)
            #(nproc, working_dir, binary, args, keywords) = task_data
            try:
                task_id = self.services.launch_task(task.nproc, task.working_dir, task.binary,
                                                    *task.args, **task.keywords)
            except ipsExceptions.InsufficientResourcesException:
                self.blocked_tasks[task_name] = task
            else:
                self.active_tasks[task_id] = task
                submit_count += 1
        if block:
            self._wait_active_tasks()
        return submit_count

    def get_finished_tasks_status(self):
        """
        Return a dictionary of exit status values for all tasks that have
        finished since the last time finished tasks were polled.
        """
        if (len(self.active_tasks) + len(self.finished_tasks) == 0):
            raise Exception('No more active tasks in task pool %s' % (self.name))

        exit_status = {}
        self._wait_any_task()
        for task_name in self.finished_tasks.keys():
            task = self.finished_tasks.pop(task_name)
            exit_status[task_name] = task.exit_status
        return exit_status

    def terminate_tasks(self):
        """
        Kill all active tasks, clear all queued, blocked and finished tasks.
        """
        if (len(self.active_tasks) > 0):
            for task_id in self.active_tasks.keys():
                self.services.kill_task(task_id)
        self.queued_tasks={}
        self.blocked_tasks={}
        self.active_tasks={}
        self.finished_tasks={}
        return

class Task(object):
    """
    Container for task information:

    * *name*: task name
    * *nproc*: number of processes the task needs
    * *working_dir*: location to launch task from
    * *binary*: full path to executable to launch
    * *\*args*: arguments for *binary*
    * *\*\*keywords*: keyword arguments for launching the task.  See :py:meth:`ServicesProxy.launch_task` for details.
    """
    def __init__(self, task_name, nproc, working_dir, binary, *args, **keywords):
        self.name = task_name
        self.nproc = int(nproc)
        self.working_dir = working_dir
        self.binary = binary
        self.args = args
        self.keywords = keywords
        self.exit_status = None
