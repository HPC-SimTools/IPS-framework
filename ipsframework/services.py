# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
import queue
import os
import subprocess

import time
import shutil
import logging
import logging.handlers
import signal
import glob
import weakref
import inspect
from . import messages, ipsutil, component
from .configobj import ConfigObj
from .cca_es_spec import initialize_event_service
from .ips_es_spec import eventManager


def launch(binary, task_name, working_dir, *args, **keywords):
    os.chdir(working_dir)
    task_stdout = sys.stdout
    try:
        log_filename = keywords["logfile"]
    except KeyError:
        pass
    else:
        task_stdout = open(log_filename, "w")

    task_stderr = subprocess.STDOUT
    try:
        err_filename = keywords["errfile"]
    except KeyError:
        pass
    else:
        try:
            task_stderr = open(err_filename, "w")
        except Exception:
            pass

    task_env = {}
    try:
        task_env = keywords["task_env"]
    except Exception:
        pass
    new_env = os.environ.copy()
    new_env.update(task_env)

    timeout = 1.e9
    try:
        timeout = float(keywords["timeout"])
    except Exception:
        pass

    print(f"Task {task_name} timeout = {timeout}")

    ret_val = None
    if isinstance(binary, str):
        cmd = f"{binary} {' '.join(map(str, args))}"
        # print(f"{asctime()} {task_name} running {cmd} on {myid} in {working_dir}", args, keywords)
        cmd_lst = cmd.split()
        process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                   stderr=task_stderr,
                                   cwd=working_dir,
                                   preexec_fn=os.setsid,
                                   env=new_env)
        start = time.time()
        while time.time() - start < timeout:
            print(f"Task {task_name} going to sleep")
            time.sleep(1.0)
            print(f"Task {task_name} Woke up")
            ret_val = process.poll()
            if ret_val is None:
                continue
            else:
                break
        else:               # Time out for process execution
            print(f"Task {task_name} timed out after {timeout} Seconds")
            os.killpg(process.pid, signal.SIGKILL)
            ret_val = -1
        # print(f"{asctime()} {task_name} : {args} Done on {myid}")
    else:
        ret_val = binary(*args)

    return task_name, ret_val


class ServicesProxy:

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
        self.dask_preload = "dask_preload.py"

    def __initialize__(self, component_ref):
        """
        Initialize the service proxy object, connecting it to its associated
        component.

        This method is for use only by the IPS framework.
        """

        self.component_ref = weakref.proxy(component_ref)
        conf = self.component_ref.config
        self.full_comp_id = '_'.join([conf['CLASS'], conf['SUB_CLASS'],
                                      conf['NAME'],
                                      str(self.component_ref.component_id.get_seq_num())])
        #
        # Set up logging path to the IPS logging daemon
        #
        socketHandler = logging.handlers.SocketHandler(self.log_pipe_name, None)
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
                raise Exception("Bad 'NODE_ALLOCATION_MODE' value %s")
        except Exception:
            if self.sim_conf['NODE_ALLOCATION_MODE'] == 'SHARED':
                self.shared_nodes = True
            else:
                self.shared_nodes = False

        # ------------------
        # set component ppn
        # ------------------
        try:
            self.ppn = int(conf['PROCS_PER_NODE'])
        except Exception:
            self.ppn = 0

        if self.sim_conf['SIMULATION_MODE'] == 'RESTART':
            if self.sim_conf['RESTART_TIME'] == 'LATEST':
                chkpts = glob.glob(os.path.join(self.sim_conf['RESTART_ROOT'], 'restart', '*'))
                base_dir = sorted(chkpts, key=lambda d: float(os.path.basename(d)))[-1]
                self.sim_conf['RESTART_TIME'] = os.path.basename(base_dir)

        # Get path to IPS modules and PYTHONPATH
        pypath = [os.path.dirname(inspect.getabsfile(component))]
        try:
            pypath.extend(os.environ["PYTHONPATH"].split(":"))
        except KeyError:
            pass

        preload_txt = "import sys;"
        for d in pypath:
            preload_txt += f"sys.path.insert(0,'{d}');"

        # print(pypath)
        # print(preload_txt)
        self.dask_preload = os.path.join(os.getcwd(), self.dask_preload)
        open(self.dask_preload, "w").write(preload_txt)

    def _init_event_service(self):
        """
        Initialize connection to the central framework event service
        """
        self.debug('_init_event_service(): self.counter = %d - %s',
                   self.counter, str(self.component_ref))
        self.counter = self.counter + 1
        initialize_event_service(self)
        self.event_service = eventManager(self.component_ref)

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
        while not finish:
            try:
                response = self.svc_response_q.get(block, timeout)
                response_list.append(response)
            except queue.Empty:
                if not block:
                    finish = True
                elif len(response_list) > 0:
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
        # print 'in _wait_msg_response'
        if msg_id in list(self.finished_calls.keys()):
            response = self.finished_calls[msg_id]
            del self.finished_calls[msg_id]
            return response
        elif msg_id not in list(self.incomplete_calls.keys()):
            self.error('Invalid call ID : %s ', str(msg_id))
            raise Exception('Invalid message request ID argument')

        keep_going = True
        while keep_going:
            # get new messages, block until something interesting comes along
            responses = self._get_incoming_responses(block)
            for r in responses:
                # time to die!
                if r.__class__ == messages.ExitMessage:
                    self.debug('%s Exiting', str(self.component_ref.component_id))
                    if r.status == messages.Message.SUCCESS:
                        sys.exit(0)
                    else:
                        sys.exit(1)
                # response to my message
                elif r.__class__ == messages.ServiceResponseMessage:
                    if (r.request_msg_id not in
                            list(self.incomplete_calls.keys())):
                        self.error('Mismatched service response msg_id %s',
                                   str(r.request_msg_id))
                        #                        dumpAll()
                        raise Exception('Mismatched service response msg_id.')
                    else:
                        del self.incomplete_calls[msg_id]
                        self.finished_calls[r.request_msg_id] = r
                        if r.request_msg_id == msg_id:
                            keep_going = False
                # some weird message came through
                else:
                    self.error('Unexpected service response of type %s',
                               r.__class__.__name__)
                    #                    dumpAll()
                    raise Exception('Unexpected service response of type ' +
                                    r.__class__.__name__)

            if not block:
                keep_going = False
        # if this message corresponds to a finish invocation, return the response message
        if msg_id in list(self.finished_calls.keys()):
            response = self.finished_calls[msg_id]
            del self.finished_calls[msg_id]
            #            dumpAll()
            return response
        #        dumpAll()
        return None

    def _invoke_service(self, component_id, method_name, *args, **keywords):
        r"""
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
        # print "in _get_service_response"
        self.debug('_get_service_response(%s)', str(msg_id))
        response = self._wait_msg_response(msg_id, block)
        self.debug('_get_service_response(%s), response = %s', str(msg_id), str(response))
        if response is None:
            return None
        if response.status == messages.Message.FAILURE:
            self.debug('###### Raising %s', str(response.args[0]))
            raise response.args[0]
        if len(response.args) > 1:
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
        if self.monitor_url:
            portal_data['vizurl'] = self.monitor_url.split('//')[-1]

        event_data = {}
        event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
        event_data['real_sim_name'] = self.sim_name
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTAL_EVENT', event_data)

    def get_port(self, port_name):
        """
        Return a reference to the component implementing port *port_name*.
        """
        msg_id = self._invoke_service(self.fwk.component_id,
                                      'get_port', port_name)
        response = self._get_service_response(msg_id, True)
        return response

    def cleanup(self):
        """
        Clean up any state from the services.  Called by the terminate method
        in the base class for components.
        """
        for (p, _, _) in self.task_map.values():
            try:
                p.kill()
            except Exception:
                pass

    def call_nonblocking(self, component_id, method_name, *args, **keywords):
        r"""
        Invoke method *method_name* on component *component_id* with optional
        arguments *\*args*.  Return *call_id*.
        """
        target_class = component_id.get_class_name()
        target_seqnum = component_id.get_seq_num()
        target = target_class + '@' + str(target_seqnum)
        formatted_args = ['%.3f' % (x) if isinstance(x, float)
                          else str(x) for x in args]
        if keywords:
            formatted_args += ["%s=" % k + str(v) for (k, v) in keywords.items()]
        self._send_monitor_event('IPS_CALL_BEGIN', 'Target = ' +
                                 target + ':' + method_name + '(' +
                                 ' ,'.join(formatted_args) + ')')
        msg_id = self._invoke_service(component_id,
                                      'init_call',
                                      method_name, *args, **keywords)
        call_id = self._get_service_response(msg_id, True)
        self.call_targets[call_id] = (target, method_name, args)
        return call_id

    def call(self, component_id, method_name, *args, **keywords):
        r"""
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
                                 target + ':' + method_name + '(' +
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
            except Exception as e:
                self.exception('Caught exception in wait_call()')
                caught_exceptions.append(e)
            else:
                if ret_val is not None:
                    ret_map[call_id] = ret_val
        if len(caught_exceptions) > 0:
            self.error('Caught one or more exceptions in call to wait_call_list')
            raise caught_exceptions[0]
        return ret_map

    def launch_task(self, nproc, working_dir, binary, *args, **keywords):
        r"""
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
        args = tuple(str(a) for a in args)
        tokens = binary.split()
        if len(tokens) > 1:
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
        except Exception:
            pass

        block = True
        try:
            block = keywords['block']
        except Exception:
            pass

        tag = 'None'
        try:
            tag = keywords['tag']
        except Exception:
            pass

        try:
            whole_nodes = keywords['whole_nodes']
            # print ">>>> value of whole_nodes", whole_nodes
        except Exception:
            if self.shared_nodes:
                whole_nodes = False
            else:
                whole_nodes = True

        try:
            whole_socks = keywords['whole_sockets']
            # print ">>>> value of whole_socks", whole_socks
        except Exception:
            if self.shared_nodes:
                whole_socks = False
            else:
                whole_socks = True

        # print "about to call init task"
        try:
            # SIMYAN: added working_dir to component method invocation
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'init_task', nproc, binary_fullpath,
                                          working_dir, task_ppn, block,
                                          whole_nodes, whole_socks, *args)
            (task_id, command, env_update) = self._get_service_response(msg_id, block=True)
        except Exception:
            # self.exception('Error initiating task %s %s on %d nodes' %  (binary, str(args), int(nproc)))
            raise

        log_filename = None
        try:
            log_filename = keywords['logfile']
        except KeyError:
            pass

        timeout = 1.e9
        try:
            timeout = keywords["timeout"]
        except KeyError:
            pass

        task_stdout = sys.stdout
        if log_filename:
            try:
                task_stdout = open(log_filename, 'w')
            except Exception:
                self.exception('Error opening log file %s : using stdout', log_filename)

        task_stderr = subprocess.STDOUT
        try:
            err_filename = keywords['errfile']
        except KeyError:
            pass
        else:
            try:
                task_stderr = open(err_filename, 'w')
            except Exception:
                self.exception('Error opening stderr file %s : using stderr', err_filename)

        cmd_lst = command.split(' ')
        if not cmd_lst[-1]:
            # Kill the last argument in the command list if it is the empty string
            cmd_lst.pop()

        try:
            self.debug('Launching command : %s', command)
            if env_update:
                new_env = os.environ
                new_env.update(env_update)
                process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                           stderr=task_stderr,
                                           cwd=working_dir,
                                           env=new_env)
            else:
                process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                           stderr=task_stderr,
                                           cwd=working_dir)
        except Exception:
            self.exception('Error executing command : %s', command)
            raise
        self._send_monitor_event('IPS_LAUNCH_TASK', 'task_id = %s , Tag = %s , nproc = %d , Target = %s' %
                                 (str(task_id), tag, int(nproc), command))

        # FIXME: process Monitoring Command : ps --no-headers -o pid,state pid1  pid2 pid3 ...

        self.task_map[task_id] = (process, time.time(), timeout)
        return task_id  # process.pid

    def launch_task_resilient(self, nproc, working_dir, binary, *args, **keywords):
        """
        **not used**
        """
        task_ppn = self.ppn
        try:
            task_ppn = keywords['task_ppn']
        except Exception:
            pass

        block = True
        try:
            block = keywords['block']
        except Exception:
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
        except Exception:
            self.exception('Error initiating task %s %s on %d nodes' %
                           (binary, str(args), int(nproc)))
            raise

        log_filename = None
        try:
            log_filename = keywords['logfile']
        except KeyError:
            pass

        task_stdout = sys.stdout
        if log_filename:
            try:
                task_stdout = open(log_filename, 'w')
            except Exception:
                self.exception('Error opening log file %s : using stdout', log_filename)

        cmd_lst = command.split(' ')
        try:
            self.debug('Launching command : %s', command)
            if env_update:
                new_env = os.environ
                new_env.update(env_update)
                process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                           stderr=subprocess.STDOUT,
                                           cwd=working_dir,
                                           env=new_env)
            else:
                process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                           stderr=subprocess.STDOUT,
                                           cwd=working_dir)
        except Exception:
            self.exception('Error executing command : %s', command)
            raise
        self._send_monitor_event('IPS_LAUNCH_TASK', 'Target = ' + command +
                                 ', task_id = ' + str(task_id))

        # FIXME: process Monitoring Command : ps --no-headers -o pid,state pid1
        # pid2 pid3 ...

        self.task_map[task_id] = (process, time.time(), nproc, working_dir, binary,
                                  args, keywords)
        return task_id  # process.pid

    def launch_task_pool(self, task_pool_name, launch_interval=0.0):
        """
        Construct messages to task manager to launch each task.
        Used by :py:class:`TaskPool` to launch tasks in a task_pool.
        """

        task_pool = self.task_pools[task_pool_name]
        queued_tasks = task_pool.queued_tasks
        submit_dict = {}
        for (task_name, task) in queued_tasks.items():
            # (nproc, working_dir, binary, args, keywords) = queued_tasks[task_name]
            task_ppn = self.ppn
            try:
                task_ppn = task.keywords['task_ppn']
            except Exception:
                pass
            try:
                wnodes = task.keywords['whole_nodes']
            except Exception:
                if self.shared_nodes:
                    wnodes = False
                else:
                    wnodes = True
            try:
                wsocks = task.keywords['whole_sockets']
            except Exception:
                if self.shared_nodes:
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
        except Exception:
            self.exception('Error initiating task pool %s ', task_pool_name)
            raise

        active_tasks = {}
        for task_name in list(allocated_tasks.keys()):
            if launch_interval > 0:
                time.sleep(launch_interval)
            # (nproc, working_dir, binary, args, keywords) = queued_tasks[task_name]
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

            timeout = 1.e9
            try:
                timeout = task.keywords["timeout"]
            except KeyError:
                pass

            task_stdout = sys.stdout
            if log_filename:
                try:
                    task_stdout = open(log_filename, 'w')
                except Exception:
                    self.exception('Error opening log file %s : using stdout', log_filename)

            task_stderr = subprocess.STDOUT
            try:
                err_filename = task.keywords['errfile']
            except KeyError:
                pass
            else:
                try:
                    task_stderr = open(err_filename, 'w')
                except Exception:
                    self.exception('Error opening stderr file %s : using stderr', err_filename)

            cmd_lst = command.split(' ')
            try:
                self.debug('Launching command : %s', command)
                if env_update:
                    new_env = os.environ
                    new_env.update(env_update)
                    process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                               stderr=task_stderr,
                                               cwd=task.working_dir,
                                               env=new_env)
                else:
                    process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                               stderr=task_stderr,
                                               cwd=task.working_dir)
            except Exception:
                self.exception('Error executing task %s - command : %s', task_name, command)
                raise
            self._send_monitor_event('IPS_LAUNCH_TASK_POOL',
                                     'task_id = %s , Tag = %s , nproc = %d , Target = %s , task_name = %s' %
                                     (str(task_id), str(tag), int(task.nproc), command, task_name))

            self.task_map[task_id] = (process, time.time(), timeout)
            active_tasks[task_name] = task_id
        return active_tasks

    def kill_task(self, task_id):
        """
        Kill launched task *task_id*.  Return if successful.  Raises exceptions if the task or process cannot be found or killed successfully.
        """
        try:
            process, _, _ = self.task_map[task_id]
            # TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
            # process, start_time = self.task_map[task_id][0], self.task_map[task_id][1]
        except KeyError:
            self.exception('Error: unrecognizable task_id = %s ', task_id)
            raise  # do we really want to raise an error or just return?
        task_retval = 'killed'
        # kill process
        try:
            process.terminate()
        except Exception:
            self.exception('exception during process termination for task %d', task_id)
            raise

        del self.task_map[task_id]
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'finish_task', task_id, task_retval)
            self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error finalizing task  %s', task_id)
            raise

    def kill_all_tasks(self):
        """
        Kill all tasks associated with this component.
        """
        while len(self.task_map) > 0:
            try:
                self.kill_task(self.task_map[0])
            except Exception:
                raise

    def wait_task_nonblocking(self, task_id):
        """Check the status of task *task_id*.  If it has finished, the
        return value is populated with the actual value, otherwise
        ``None`` is returned.  A *KeyError* exception may be raised if
        the task is not found.

        """
        try:
            process, start_time, timeout = self.task_map[task_id]
            # TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
            # process, start_time = self.task_map[task_id][0], self.task_map[task_id][1]
        except KeyError:
            self.exception('Error: unrecognizable task_id = %s ', task_id)
            raise
        task_retval = process.poll()
        if task_retval is None:
            if start_time + timeout < time.time():
                self.kill_task(task_id)
                self._send_monitor_event('IPS_TASK_END', 'task_id = %s  TIMEOUT elapsed time = %.2f S' %
                                         (str(task_id), time.time() - start_time))
                return -1
            else:
                return None
        else:
            retval = self.wait_task(task_id)
            return retval

    def wait_task(self, task_id, timeout=-1, delay=1):
        """Check the status of task *task_id*.  Return the return value of
        the task when finished successfully.  Raise exceptions if the
        task is not found, or if there are problems finalizing the
        task.

        """
        # print "in wait task"
        try:
            process, start_time, _ = self.task_map[task_id]
        except KeyError:
            self.exception('Error: unrecognizable task_id = %s ', str(task_id))
            raise
        task_retval = None
        if timeout < 0:
            task_retval = process.wait()
        else:
            maxtime = start_time + timeout
            while time.time() < maxtime:
                task_retval = process.poll()
                if task_retval is None:
                    time.sleep(delay)
                else:
                    break
        if task_retval is None:
            process.kill()
            task_retval = process.wait()
            self._send_monitor_event('IPS_TASK_END', 'task_id = %s  TIMEOUT elapsed time = %.2f S' %
                                     (str(task_id), time.time() - start_time))
        else:
            self._send_monitor_event('IPS_TASK_END', 'task_id = %s  elapsed time = %.2f S' %
                                     (str(task_id), time.time() - start_time))

        del self.task_map[task_id]
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'finish_task', task_id, task_retval)
            self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error finalizing task  %s', task_id)
            raise
        return task_retval

    def wait_task_resilient(self, task_id):
        """
        **not used**
        """
        try:
            process, start_time, nproc, working_dir, binary, args, keywords = self.task_map[task_id]
        except KeyError:
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
        except Exception:
            self.exception('Error finalizing task  %s', task_id)
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
                if ('relaunch' not in keywords) or (keywords['relaunch'] != 'N'):
                    relaunch_task_id = self.launch_task_resilient(nproc, working_dir, binary, args, keywords)
                    self.debug('Relaunched failed task.')
                    return self.wait_task_resilient(relaunch_task_id)
                else:
                    self.debug('Task failed but was not relaunched.')

        return task_retval

    def wait_tasklist(self, task_id_list, block=True):
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
        while len(running_tasks) > 0:
            for task_id in task_id_list:
                if task_id not in running_tasks:
                    continue
                process = self.task_map[task_id][0]
                retval = process.poll()
                if retval is not None:
                    task_retval = self.wait_task(task_id)
                    ret_dict[task_id] = task_retval
                    running_tasks.remove(task_id)
            if not block:
                break
            time.sleep(0.05)
        return ret_dict

    def get_config_param(self, param, silent=False):
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
                if not silent:
                    self.exception('Error retrieving value of config parameter %s', param)
                raise
        return val

    def set_config_param(self, param, value, target_sim_name=None):
        """
        Set configuration parameter *param* to *value*.  Raise exceptions if
        the parameter cannot be changed or if there are problems setting the
        value.
        """
        if target_sim_name is None:
            sim_name = self.sim_name
        else:
            sim_name = target_sim_name
        if param in list(self.sim_conf.keys()):
            raise Exception('Cannot dynamically alter simulation configuration parameter ' + param)
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'set_config_parameter', param, value, sim_name)
            retval = self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error setting value of configuration parameter %s', param)
            raise
        return retval

    def get_time_loop(self):
        """
        Return the list of times as specified in the configuration file.
        """
        if self.time_loop is not None:
            return self.time_loop
        sim_conf = self.sim_conf
        tlist = []
        time_conf = sim_conf['TIME_LOOP']

        def safe(nums):
            return len(set(str(nums)).difference(set("1234567890-+/*.e "))) == 0
        # generate tlist in regular mode (start, finish, step)
        if time_conf['MODE'] == 'REGULAR':
            for entry in ['FINISH', 'START', 'NSTEP']:
                if not safe(time_conf[entry]):
                    self.exception('Invalid TIME_LOOP value of %s = %s' % (entry, time_conf[entry]))
                    raise Exception('Invalid TIME_LOOP value of %s = %s' % (entry, time_conf[entry]))
            finish = float(eval(time_conf['FINISH']))
            start = float(eval(time_conf['START']))
            nstep = int(eval(time_conf['NSTEP']))
            step = (finish - start) / nstep
            tlist = [start + step * n for n in range(nstep + 1)]
        # generate tlist in explicit mode (list of times)
        elif time_conf['MODE'] == 'EXPLICIT':
            tlist = [float(v) for v in time_conf['VALUES'].split()]
        self.time_loop = tlist
        return tlist

    def checkpoint_components(self, comp_id_list, time_stamp, Force=False, Protect=False):
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
        if Force:
            return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
        try:
            chkpt_conf = self.sim_conf['CHECKPOINT']
            mode = chkpt_conf['MODE']
            num_chkpt = int(chkpt_conf['NUM_CHECKPOINT'])
        except KeyError:
            self.error('Missing CHECKPOINT config section, or one of the required parameters: MODE, NUM_CHECKPOINT')
            self.exception('Error accessing CHECKPOINT section in config file')
            raise

        if num_chkpt == 0:
            return None

        if (mode not in ['ALL', 'WALLTIME_REGULAR', 'WALLTIME_EXPLICIT',
                         'PHYSTIME_REGULAR', 'PHYSTIME_EXPLICIT']):
            self.error('Invalid MODE = %s in checkpoint configuration', mode)
            raise Exception('Invalid MODE = %s in checkpoint configuration' % (mode))

        if mode == 'ALL':
            return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)

        if mode == 'WALLTIME_REGULAR':
            interval = float(chkpt_conf['WALLTIME_INTERVAL'])
            if self.cur_time - self.last_ckpt_walltime >= interval:
                return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
            else:
                return None
        elif mode == 'WALLTIME_EXPLICIT':
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
        elif mode == 'PHYSTIME_REGULAR':
            pt_interval = float(chkpt_conf['PHYSTIME_INTERVAL'])
            pt_current = float(time_stamp)
            pt_start = self.time_loop[0]
            if self.last_ckpt_phystime is None:
                self.last_ckpt_phystime = pt_start
            if pt_current - self.last_ckpt_phystime >= pt_interval:
                return self._dispatch_checkpoint(time_stamp, comp_id_list, Protect)
            else:
                return None
        elif mode == 'PHYSTIME_EXPLICIT':
            # print ">>>>>>> chkpt_conf['PHYSTIME_VALUES'] = ", chkpt_conf['PHYSTIME_VALUES']
            try:
                pt_values = chkpt_conf['PHYSTIME_VALUES'].split()
            except AttributeError:
                pt_values = chkpt_conf['PHYSTIME_VALUES']
            pt_values = [float(t) for t in pt_values]
            # print ">>>>>>> pt_values = ", pt_values
            pt_current = float(time_stamp)
            for pt in pt_values:
                if pt_current >= pt > self.last_ckpt_phystime:
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
                   self.last_ckpt_walltime - self.start_time, self.last_ckpt_phystime)
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
        if num_chkpt <= 0:
            return ret_dict

        base_dir = os.path.join(sim_root, 'restart')
        timeStamp_str = '%0.3f' % (float(time_stamp))
        self.new_chkpts.append(timeStamp_str)
        try:
            protect_freq = chkpt_conf['PROTECT_FREQUENCY']
        except KeyError:
            pass
        else:
            if Protect or (self.chkpt_counter % int(protect_freq) == 0):
                self.protected_chkpts.append(timeStamp_str)

        if os.path.isdir(base_dir):
            all_chkpts = [os.path.basename(f) for f in glob.glob(os.path.join(base_dir, '*'))
                          if os.path.isdir(f)]
            prior_runs_chkpts_dirs = [chkpt for chkpt in all_chkpts if chkpt not in self.new_chkpts]
            purge_candidates = sorted(prior_runs_chkpts_dirs, key=float)
            purge_candidates += [chkpt for chkpt in self.new_chkpts if (chkpt in all_chkpts and
                                                                        chkpt not in self.protected_chkpts)]
            #            self.debug('CHECKPOINT: all_chkpts = %s', str(all_chkpts))
            #            self.debug('CHECKPOINT: purge_candidates = %s', str(purge_candidates))
            #            self.debug('CHECKPOINT: protected_chkpts = %s', str(self.protected_chkpts))
            #            self.debug('CHECKPOINT: ***********************')
            while len(purge_candidates) > num_chkpt:
                obsolete_chkpt = purge_candidates.pop(0)
                chkpt_dir = os.path.join(base_dir, obsolete_chkpt)
                try:
                    shutil.rmtree(chkpt_dir)
                except Exception:
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
        if self.workdir == '':
            self.workdir = os.path.join(self.sim_conf['SIM_ROOT'], 'work',
                                        self.full_comp_id)
        return self.workdir

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
            outprefix = self.sim_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''

        targetdir = os.path.join(simroot, 'simulation_setup',
                                 self.full_comp_id)
        try:
            # print 'inputDir =', inputDir
            # print 'input_file_list =', input_file_list
            # print 'targetdir =', targetdir
            # print 'outprefix =', outprefix

            ipsutil.copyFiles(inputDir, input_file_list, targetdir, outprefix)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_INPUTS',
                                     'Files = ' + str(input_file_list) +
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error in stage_input_files')
            raise e
        for (_, old_conf, _, _) in self.sub_flows.values():
            ports = old_conf['PORTS']['NAMES'].split()
            comps = [old_conf['PORTS'][p]['IMPLEMENTATION'] for p in ports]
            for c in comps:
                input_dir = old_conf[c]['INPUT_DIR']
                input_files = old_conf[c]['INPUT_FILES']
                # print('---- Staging inputs for %s:%s' % (name, c))
                input_target_dir = os.path.join(os.getcwd(), c)
                try:
                    os.mkdir(input_target_dir)
                except OSError as e:
                    if e.errno != 17:
                        raise
                try:
                    ipsutil.copyFiles(input_dir, input_files, input_target_dir)
                except Exception as e:
                    self._send_monitor_event('IPS_STAGE_INPUTS',
                                             'Files = ' + str(input_files) +
                                             ' Exception raised : ' + str(e),
                                             ok='False')
                    self.exception('Error in stage_input_files')
                    raise e
        elapsed_time = time.time() - start_time
        self._send_monitor_event(eventType='IPS_STAGE_INPUTS',
                                 comment='Elapsed time = %.3f Path = %s Files = %s' %
                                         (elapsed_time, os.path.abspath(inputDir),
                                          str(input_file_list)))

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
            outprefix = self.sim_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''

        targetdir = os.path.join(simroot, 'simulation_setup',
                                 self.full_comp_id)
        try:
            ipsutil.copyFiles(dataDir, data_file_list, targetdir, outprefix)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_DATA',
                                     'Files = ' + str(data_file_list) +
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error in stage_data_files')
            raise e
        self._send_monitor_event('IPS_STAGE_DATA', 'Files = ' + str(data_file_list))

    def stage_nonPS_output_files(self, timeStamp, file_list, keep_old_files=True):
        """
        Same as stage_output_files, but does not do anything with the Plasma State.
        """
        workdir = self.get_working_dir()
        sim_root = self.sim_conf['SIM_ROOT']
        try:
            outprefix = self.sim_conf['OUTPUT_PREFIX']
        except KeyError:
            outprefix = ''
        out_root = 'simulation_results'

        output_dir = os.path.join(sim_root, out_root,
                                  str(timeStamp), 'components',
                                  self.full_comp_id)
        try:
            ipsutil.copyFiles(workdir, file_list, output_dir, outprefix,
                              keep_old=keep_old_files)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                     'Files = ' + str(file_list) +
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error in stage_nonPS_output_files()')
            raise

        # Store symlinks to component output files in a single top-level directory

        symlink_dir = os.path.join(sim_root, out_root, self.full_comp_id)
        try:
            os.makedirs(symlink_dir)
        except OSError as e:
            if e.errno != 17:
                self.exception('Error creating directory %s : %s',
                               symlink_dir, e.strerror)
                raise

        all_files = sum([glob.glob(f) for f in file_list.split()], [])

        for f in all_files:
            real_file = os.path.join(output_dir, outprefix + f)
            tokens = f.rsplit('.', 1)
            if len(tokens) == 1:
                newName = '_'.join([f, str(timeStamp)])
            else:
                name = tokens[0]
                ext = tokens[1]
                newName = '_'.join([name, str(timeStamp)]) + '.' + ext
            sym_link = os.path.join(symlink_dir, newName)
            if os.path.isfile(sym_link):
                os.remove(sym_link)
            # We need to use relative path for the symlinks
            common1 = os.path.commonprefix([real_file, sym_link])
            (head, _, _) = common1.rpartition('/')
            common = head.split('/')
            file_suffix = real_file.split('/')[len(common):]  # Include file name
            link_suffix = sym_link.split('/')[len(common):-1]  # No file name
            p = []
            if len(link_suffix) > 0:
                p = ['../' * len(link_suffix)]
            p = p + file_suffix
            relpath = os.path.join(*p)
            os.symlink(relpath, sym_link)

        self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                 'Files = ' + str(file_list))

    def stage_PS_output_files(self, timeStamp, file_list, keep_old_files=True):
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

        # Store plasma state files into $SIM_ROOT/history/plasma_state
        # Plasma state files are renamed, by appending the full component
        # name (CLASS_SUBCLASS_NAME) and timestamp to the file name.
        # A version number is added to the end of the file name to avoid
        # overwriting existing plasma state files
        plasma_dir = os.path.join(sim_root,
                                  out_root,
                                  'Plasma_state')
        try:
            os.makedirs(plasma_dir)
        except OSError as e:
            if e.errno != 17:
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                         'Files = ' + str(file_list) +
                                         ' Exception raised : ' + e.strerror,
                                         ok='False')
                self.exception('Error creating directory %s : %d-%s',
                               plasma_dir, e.errno, e.strerror)
                raise

        try:
            state_files = conf['STATE_FILES'].split()
        except KeyError:
            state_files = self.get_config_param('STATE_FILES').split()

        all_plasma_files = []
        for plasma_file in state_files:
            globbed_files = glob.glob(plasma_file)
            if len(globbed_files) > 0:
                all_plasma_files += globbed_files

        for f in all_plasma_files:
            if not os.path.isfile(f):
                continue
            tokens = f.split('.')
            if len(tokens) == 1:
                newName = '_'.join([outprefix + f, self.full_comp_id, str(timeStamp)])
            else:
                name = '.'.join(tokens[:-1])
                ext = tokens[-1]
                newName = '_'.join([outprefix + name, self.full_comp_id, str(timeStamp)]) + \
                          '.' + ext
            target_name = os.path.join(plasma_dir, newName)
            if os.path.isfile(target_name):
                for i in range(1000):
                    newName = target_name + '.' + str(i)
                    if os.path.isfile(newName):
                        continue
                    target_name = newName
                    break
            try:
                shutil.copy(f, target_name)
            except (IOError, os.error) as why:
                self.exception('Error copying file: %s from %s to %s - %s',
                               f, workdir, target_name, str(why))
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                         'Files = ' + str(file_list) +
                                         ' Exception raised : ' + str(why),
                                         ok='False')
                raise

        self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                 'Files = ' + str(file_list))

    def stage_subflow_output_files(self, subflow_name='ALL'):
        # Gather outputs from sub-workflows. Sub-workflow output
        # is defined to be the output files from its DRIVER component
        # as they exist in the sub-workflow driver's work area at the
        # end of the sub-simulation. If subflow_name != 'ALL' then get
        # output from only that sub-flow
        subflow_dict = {}
        if subflow_name == 'ALL':
            subflow_dict = self.sub_flows
        else:
            try:
                subflow_dict[subflow_name] = self.sub_flows[subflow_name]
            except KeyError:
                self.exception("Subflow name %s not found" % subflow_name)
                raise Exception("Subflow name %s not found" % subflow_name)

        return_dict = {}
        for (sim_name, (sub_conf_new, _, _, driver_comp)) in subflow_dict.items():
            driver = sub_conf_new[sub_conf_new['PORTS']['DRIVER']['IMPLEMENTATION']]
            output_dir = os.path.join(sub_conf_new['SIM_ROOT'], 'work',
                                      '_'.join([driver['CLASS'], driver['SUB_CLASS'],
                                                driver['NAME'],
                                                str(driver_comp.get_seq_num())]))
            # print '################',  output_dir
            output_files = driver['OUTPUT_FILES']
            try:
                ipsutil.copyFiles(output_dir, output_files, self.get_working_dir(), keep_old=False)
            except Exception as e:
                self._send_monitor_event('IPS_STAGE_SUBFLOW_OUTPUTS',
                                         'Files = ' + str(output_files) +
                                         ' Exception raised : ' + str(e),
                                         ok='False')
                self.exception('Error in stage_subflow_output_files() for subflow %s' % sim_name)
                raise
            else:
                if isinstance(output_files, str):
                    return_dict[sim_name] = output_files.split()
                else:
                    return_dict[sim_name] = output_files
        return return_dict

    def stage_output_files(self, timeStamp, file_list, keep_old_files=True, save_plasma_state=True):
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

        output_dir = os.path.join(sim_root, out_root,
                                  str(timeStamp), 'components',
                                  self.full_comp_id)
        if type(file_list).__name__ == 'str':
            file_list = file_list.split()
        all_files = sum([glob.glob(f) for f in file_list], [])
        try:
            ipsutil.copyFiles(workdir, all_files, output_dir, outprefix,
                              keep_old=keep_old_files)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                     'Files = ' + str(file_list) +
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
        except OSError as e:
            if e.errno != 17:
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                         'Files = ' + str(file_list) +
                                         ' Exception raised : ' + e.strerror,
                                         ok='False')
                self.exception('Error creating directory %s : %d-%s',
                               plasma_dir, e.errno, e.strerror)
                raise

        all_plasma_files = []
        if save_plasma_state:
            try:
                state_files = conf['STATE_FILES'].split()
            except KeyError:
                state_files = self.get_config_param('STATE_FILES').split()
            for plasma_file in state_files:
                globbed_files = glob.glob(plasma_file)
                if len(globbed_files) > 0:
                    all_plasma_files += globbed_files

        for f in all_plasma_files:
            if not os.path.isfile(f):
                continue
            tokens = f.split('.')
            if len(tokens) == 1:
                newName = '_'.join([outprefix + f, self.full_comp_id, str(timeStamp)])
            else:
                name = '.'.join(tokens[:-1])
                ext = tokens[-1]
                newName = '_'.join([outprefix + name, self.full_comp_id, str(timeStamp)]) + \
                          '.' + ext
            target_name = os.path.join(plasma_dir, newName)
            if os.path.isfile(target_name):
                for i in range(1000):
                    newName = target_name + '.' + str(i)
                    if os.path.isfile(newName):
                        continue
                    target_name = newName
                    break
            try:
                shutil.copy(f, target_name)
            except (IOError, os.error) as why:
                self.exception('Error copying file: %s from %s to %s - %s',
                               f, workdir, target_name, str(why))
                self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                         'Files = ' + str(file_list) +
                                         ' Exception raised : ' + str(why),
                                         ok='False')
                raise

        # Store symlinks to component output files in a single top-level directory

        symlink_dir = os.path.join(sim_root, out_root, self.full_comp_id)
        try:
            os.makedirs(symlink_dir)
        except OSError as e:
            if e.errno != 17:
                self.exception('Error creating directory %s : %s',
                               symlink_dir, e.strerror)
                raise

        all_files = sum([glob.glob(f) for f in file_list], [])

        for f in all_files:
            real_file = os.path.join(output_dir, outprefix + f)
            tokens = f.rsplit('.', 1)
            if len(tokens) == 1:
                newName = '_'.join([f, str(timeStamp)])
            else:
                name = tokens[0]
                ext = tokens[1]
                newName = '_'.join([name, str(timeStamp)]) + '.' + ext
            sym_link = os.path.join(symlink_dir, newName)
            if os.path.isfile(sym_link):
                os.remove(sym_link)
            # We need to use relative path for the symlinks
            common1 = os.path.commonprefix([real_file, sym_link])
            (head, _, _) = common1.rpartition('/')
            common = head.split('/')
            file_suffix = real_file.split('/')[len(common):]  # Include file name
            link_suffix = sym_link.split('/')[len(common):-1]  # No file name
            p = []
            if len(link_suffix) > 0:
                p = ['../' * len(link_suffix)]
            p = p + file_suffix
            relpath = os.path.join(*p)
            os.symlink(relpath, sym_link)

        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_STAGE_OUTPUTS',
                                 'Elapsed time = %.3f Path = %s Files = %s' %
                                 (elapsed_time, output_dir, str(file_list)))

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
        if num_chkpt == 0:
            return
        conf = self.component_ref.config
        base_dir = os.path.join(sim_root, 'restart')
        timeStamp_str = '%0.3f' % (float(timeStamp))
        self.new_chkpts.append(timeStamp_str)

        targetdir = os.path.join(base_dir,
                                 timeStamp_str,
                                 '_'.join([conf['CLASS'],
                                           conf['SUB_CLASS'],
                                           conf['NAME']]))
        self.debug('Checkpointing: Copying %s to dir %s', str(file_list), targetdir)

        try:
            ipsutil.copyFiles(workdir, file_list, targetdir)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_RESTART',
                                     'Files = ' + str(file_list) +
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error in stage_restart_files()')
            raise

        self._send_monitor_event('IPS_SAVE_RESTART',
                                 'Files = ' + str(file_list))

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
        except Exception as e:
            self._send_monitor_event('IPS_GET_RESTART',
                                     'Files = ' + str(file_list) +
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error in get_restart_files()')
            raise

        self._send_monitor_event('IPS_GET_RESTART',
                                 'Files = ' + str(file_list))

    def stage_state(self, state_files=None):
        """
        Copy current state to work directory.
        """
        start_time = time.time()
        conf = self.component_ref.config
        if state_files:
            files = state_files
        else:
            try:
                files = conf['STATE_FILES'].split()
            except KeyError:
                files = self.get_config_param('STATE_FILES').split()

        state_dir = self.get_config_param('STATE_WORK_DIR')
        workdir = self.get_working_dir()

        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'stage_state', files, state_dir, workdir)
            self._get_service_response(msg_id, block=True)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_STATE',
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error staging state files')
            raise
        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_STAGE_STATE',
                                 'Elapsed time = %.3f  files = %s Success' %
                                 (elapsed_time, ' '.join(files)))

    def update_state(self, state_files=None):
        """
        Copy local (updated) state to global state.  If no  state
        files are specified, component configuration specification is used.
        Raise exceptions upon copy.
        """
        start_time = time.time()
        conf = self.component_ref.config
        files = ''
        if not state_files:
            try:
                files = conf['STATE_FILES'].split()
            except KeyError:
                files = self.get_config_param('STATE_FILES').split()
        else:
            files = ' '.join(state_files).split()

        state_dir = self.get_config_param('STATE_WORK_DIR')
        workdir = self.get_working_dir()
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'update_state', files, workdir, state_dir)
            self._get_service_response(msg_id, block=True)
        except Exception as e:
            print('Error updating state files', str(e))
            self._send_monitor_event('IPS_UPDATE_STATE',
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error updating state files')
            raise
        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_UPDATE_STATE',
                                 'Elapsed time = %.3f   files = %s Success' %
                                 (elapsed_time, ' '.join(files)))

    def merge_current_state(self, partial_state_file, logfile=None, merge_binary=None):
        """
        Merge partial plasma state with global state.  Partial plasma state
        contains only the values that the component contributes to the
        simulation.  Raise exceptions on bad merge.  Optional *logfile* will
        capture ``stdout`` from merge. Optional *merge_binary* specifies path
        to executable code to do the merge (default value : "update_state")
        """
        state_dir = self.get_config_param('STATE_WORK_DIR')
        current_plasma_state = self.get_config_param('CURRENT_STATE')
        work_dir = self.get_working_dir()
        if os.path.isabs(partial_state_file):
            update_file = partial_state_file
        else:
            update_file = os.path.join(work_dir, partial_state_file)

        source_plasma_file = os.path.join(state_dir, current_plasma_state)
        bin_name = merge_binary if merge_binary else "update_state"
        full_path_binary = ipsutil.which(bin_name)
        if not full_path_binary:
            self.error("Missing executable %s in PATH" % bin_name)
            raise FileNotFoundError("Missing executable file %s in PATH" % bin_name)
        try:
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'merge_current_state', update_file,
                                          source_plasma_file, logfile, full_path_binary)
            ret_val = self._get_service_response(msg_id, block=True)
        except Exception as e:
            print('Error merging state files', str(e))
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE',
                                     ' Exception raised : ' + str(e),
                                     ok='False')
            self.exception('Error merging plasma state file ' + partial_state_file)
            raise
        if ret_val == 0:
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE',
                                     'Success')
            return
        else:
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE',
                                     ' Error in call to update_state() : ',
                                     ok='False')
            self.error('Error merging update %s into current plasma state file %s',
                       partial_state_file, current_plasma_state)
            raise Exception('Error merging update %s into current plasma state file %s' %
                            (partial_state_file, current_plasma_state))

    def update_time_stamp(self, new_time_stamp=-1):
        """
        Update time stamp on portal.
        """
        event_data = {}
        event_data['sim_name'] = self.sim_name
        portal_data = {}
        portal_data['phystimestamp'] = new_time_stamp
        portal_data['eventtype'] = 'PORTALBRIDGE_UPDATE_TIMESTAMP'
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTALBRIDGE_UPDATE_TIMESTAMP', event_data)
        self._send_monitor_event('IPS_UPDATE_TIME_STAMP', 'Timestamp = ' + str(new_time_stamp))

    def _get_replay_comp_data(self, timeStamp):
        """
        Return data files from replay component at time *timeStamp*.
        """
        try:
            replay_sim_root = self.component_ref.REPLAY_SIM_ROOT
            replay_port = self.component_ref.REPLAY_PORT
            replay_config_file = self.component_ref.REPLAY_CONFIG_FILE
        except Exception:
            self.exception('Error retrieving replay configuration parameters')
            raise
        if not self.replay_conf:
            try:
                self.replay_conf = ConfigObj(replay_config_file, interpolation='template',
                                             file_error=True)
            except IOError:
                self.exception('Error opening config file: %s', replay_config_file)
                raise
        ports = self.replay_conf['PORTS']
        comp_conf = None
        try:
            comp_conf = ports[replay_port]['IMPLEMENTATION']
        except Exception:
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
        if len(comp_dirs) != 1:
            self.error('Could not find a single component instance implementing port %s',
                       replay_port)
            raise Exception('Could not find a single component instance implementing port %s ' +
                            replay_port)
        replay_comp_id = os.path.basename(comp_dirs[0])
        state_files = []
        try:
            state_files = comp_conf['STATE_FILES'].split()
        except KeyError:
            state_files = self.replay_conf['STATE_FILES'].split()

        return (comp_conf,
                outprefix,
                replay_sim_root,
                replay_comp_id,
                output_files,
                state_files)

    def stage_replay_output_files(self, timeStamp):
        """
        Copy output files from the replay component to current sim for
        physics time *timeStamp*.  Return location of new local copies.
        """
        replay_comp_data = self._get_replay_comp_data(timeStamp)
        outprefix = replay_comp_data[1]
        replay_sim_root = replay_comp_data[2]
        replay_comp_id = replay_comp_data[3]
        output_files = replay_comp_data[4]

        symlink_dir = os.path.join(replay_sim_root, 'simulation_results', replay_comp_id)
        prefix_out_files = [outprefix + f for f in output_files]
        local_output_files = []
        use_sym_link = False
        try:
            use_sym_link = self.component_ref.config['USE_SYM_LINK']
        except KeyError:
            pass
        for f in prefix_out_files:
            tokens = f.rsplit('.', 1)
            if len(tokens) == 1:
                link_name = '_'.join([f, str(timeStamp)])
            else:
                name = tokens[0]
                ext = tokens[1]
                link_name = '_'.join([name, str(timeStamp)]) + '.' + ext
            sym_link = os.path.join(symlink_dir, link_name)
            try:
                if use_sym_link:
                    try:
                        os.symlink(sym_link, f)
                    except Exception:
                        shutil.copy(sym_link, f)
                else:
                    shutil.copy(sym_link, f)
            except Exception:
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
            for (key, value) in self.replay_conf.items():
                if f == value:
                    macro_name = key
            if not macro_name:
                raise Exception('Unable to deduce macro name for file %s ' + f)
            target_name = self.get_config_param(macro_name)

            # Get name of replay file with embedded outprefix and timestamp
            tokens = f.split('.')
            if len(tokens) == 1:
                replay_fname = '_'.join([outprefix + f, replay_comp_id, str(timeStamp)])
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
                if os.path.isfile(replay_file + '.' + str(i)):
                    tmp = replay_file + '.' + str(i)
                    continue
                break
            if tmp:
                replay_file = tmp

            try:
                if use_sym_link:
                    try:
                        os.symlink(replay_file, target_name)
                    except Exception:
                        self.exception('Error creating symlink %s to %s',
                                       target_name, replay_file)
                        shutil.copy(replay_file, target_name)
                else:
                    shutil.copy(replay_file, target_name)
            except Exception:
                self.exception('Error copying replay file from %s to %s',
                               replay_file, target_name)
                self._send_monitor_event('IPS_STAGE_REPLAY_PLASMA_STATE',
                                         'Files = ' + str(replay_plasma_files) +
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
        self._send_monitor_event(eventType='IPS_SET_MONITOR_URL', comment='SUCCESS')

    def publish(self, topicName, eventName, eventBody):
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
        return self._send_monitor_event(eventType=event_type,
                                        comment=event_comment)

    def log(self, *args):
        """
        Wrapper for :py:meth:`ServicesProxy.info`.
        """
        return self.info(*args)

    def debug(self, *args):
        """
        Produce **debugging** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if len(args) > 1:
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.debug(msg)
        except Exception:
            self.error('Bad format in call to services.debug() ' + str(args))

    def info(self, *args):
        """
        Produce **informational** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if len(args) > 1:
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.info(msg)
        except Exception:
            self.error('Bad format in call to services.info() ' + str(args))

    def warning(self, *args):
        """
        Produce **warning** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if len(args) > 1:
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.warning(msg)
        except Exception:
            self.error('Bad format in call to services.warning() ' + str(args))

    def error(self, *args):
        """
        Produce **error** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if len(args) > 1:
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.error(msg)
        except Exception:
            self.error('Bad format in call to services.error() ' + str(args))

    def exception(self, *args):
        """
        Produce **exception** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if len(args) > 1:
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.exception(msg, exc_info=False)
        except Exception:
            self.error('Bad format in call to services.exception() ' + str(args))

    def critical(self, *args):
        """
        Produce **critical** message in simulation log file.  Raise exception for bad formatting.
        """
        try:
            if len(args) > 1:
                msg = args[0] % args[1:]
            else:
                msg = args[0]
            self.logger.critical(msg)
        except Exception:
            self.error('Bad format in call to services.critical() ' + str(args))

    def create_task_pool(self, task_pool_name):
        """
        Create an empty pool of tasks with the name *task_pool_name*.  Raise exception if duplicate name.
        """
        if task_pool_name in list(self.task_pools.keys()):
            raise Exception('Error: Duplicate task pool name %s' % (task_pool_name))
        self.task_pools[task_pool_name] = TaskPool(task_pool_name, self)

    def add_task(self, task_pool_name, task_name, nproc, working_dir,
                 binary, *args, **keywords):
        """
        Add task *task_name* to task pool *task_pool_name*.  Remaining arguments are the same as
        in :py:meth:`ServicesProxy.launch_task`.
        """
        task_pool = self.task_pools[task_pool_name]
        return task_pool.add_task(task_name, nproc, working_dir, binary,
                                  *args, keywords=keywords)

    def submit_tasks(self, task_pool_name, block=True, use_dask=False, dask_nodes=1,
                     dask_ppn=None, launch_interval=0.0):
        """
        Launch all unfinished tasks in task pool *task_pool_name*.  If *block* is ``True``,
        return when all tasks have been launched.  If *block* is ``False``, return when all
        tasks that can be launched immediately have been launched.  Return number of tasks
        submitted.
        """
        start_time = time.time()
        self._send_monitor_event('IPS_TASK_POOL_BEGIN', 'task_pool = %s ' % task_pool_name)
        task_pool: TaskPool = self.task_pools[task_pool_name]
        retval = task_pool.submit_tasks(block, use_dask, dask_nodes, dask_ppn, launch_interval)
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


class TaskPool:
    """
    Class to contain and manage a pool of tasks.
    """
    dask = None
    distributed = None
    try:
        dask: dask = __import__("dask")
        distributed: dask.distributed = __import__("dask.distributed",
                                                   fromlist=[None])
    except ImportError:
        pass
    else:
        dask_scheduler = None
        dask_worker = None
        dask_scheduler = shutil.which("dask-scheduler")
        dask_worker = shutil.which("dask-worker")
        if not dask_scheduler or not dask_worker:
            dask = None
            distributed = None

    def __init__(self, name, services):
        self.dask_pool = False
        self.name = name
        self.services = services
        self.active_tasks = {}
        self.finished_tasks = {}
        self.queued_tasks = {}
        self.blocked_tasks = {}
        self.serial_pool = True
        self.dask_sched_pid = None
        self.dask_workers_tid = None
        self.futures = None
        self.dask_file_name = None
        self.dask_client = None

    def _wait_any_task(self, block=True):
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
            for task_id in list(self.active_tasks.keys()):
                exit_status = self.services.wait_task_nonblocking(task_id)
                if exit_status is not None:
                    task = self.active_tasks.pop(task_id)
                    task.exit_status = exit_status
                    self.finished_tasks[task.name] = task
                    done = True
            if not done:
                if block:
                    time.sleep(0.05)
                else:
                    break

    def _wait_active_tasks(self):
        """
        Call :py:meth:`TaskPool._wait_any_task` until there are no more *active_tasks*.
        """
        while len(self.active_tasks) > 0:
            self._wait_any_task()

    def add_task(self, task_name, nproc, working_dir, binary, *args, **keywords):
        """
        Create :py:obj:`Task` object and add to *queued_tasks* of the task
        pool.  Raise exception if task name already exists in task pool.
        """
        if task_name in self.queued_tasks:
            raise Exception('Duplicate task name %s in task pool' % task_name)

        binary_fullpath = binary
        if isinstance(binary, str):
            tokens = binary.split()
            if len(tokens) > 1:
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

        # print("####", binary_fullpath, args)
        keywords['keywords']['block'] = False

        self.serial_pool = self.serial_pool and (nproc == 1)
        self.queued_tasks[task_name] = Task(task_name, nproc, working_dir, binary_fullpath, *args,
                                            **keywords["keywords"])

    def submit_dask_tasks(self, block=True, dask_nodes=1, dask_ppn=None):
        services: ServicesProxy = self.services
        self.dask_file_name = os.path.join(os.getcwd(),
                                           f".{self.name}_dask_shed_{time.time()}.json")
        self.dask_sched_pid = subprocess.Popen([self.dask_scheduler, "--no-dashboard",
                                                "--scheduler-file", self.dask_file_name, "--port", "0"]).pid

        dask_nodes = 1 if dask_nodes is None else dask_nodes
        if services.get_config_param("MPIRUN") == "eval":
            dask_nodes = 1

        nthreads = dask_ppn if dask_ppn else services.get_config_param("PROCS_PER_NODE")
        self.dask_workers_tid = services.launch_task(dask_nodes, os.getcwd(),
                                                     self.dask_worker,
                                                     "--scheduler-file",
                                                     self.dask_file_name,
                                                     "--nprocs", 1,
                                                     "--nthreads", nthreads,
                                                     "--no-dashboard",
                                                     "--preload", self.services.dask_preload,
                                                     task_ppn=1)

        self.dask_client = self.dask.distributed.Client(scheduler_file=self.dask_file_name)
        launch.__module__ = "__main__"
        self.futures = []
        for k, v in self.queued_tasks.items():
            # print(k,v, v.binary, v.args)
            try:
                log_filename = v.keywords["logfile"]
            except KeyError:
                pass
            else:
                if not os.path.isabs(log_filename):
                    full_path = os.path.join(os.getcwd(), log_filename)
                    v.keywords["logfile"] = full_path

            self.futures.append(self.dask_client.submit(launch,
                                                        v.binary,
                                                        k,
                                                        v.working_dir,
                                                        *v.args,
                                                        **v.keywords))
        self.active_tasks = self.queued_tasks
        self.queued_tasks = {}
        return len(self.futures)

    def submit_tasks(self, block=True, use_dask=False, dask_nodes=1, dask_ppn=None, launch_interval=0.0):
        """
        Launch tasks in *queued_tasks*.  Finished tasks are handled before
        launching new ones.  If *block* is ``True``, the number of tasks
        submited is returned after all tasks have been launched and
        completed.  If *block* is ``False`` the number of tasks that can
        immediately be launched is returned.
        """

        if TaskPool.dask and self.serial_pool and use_dask:
            self.dask_pool = True
            return self.submit_dask_tasks(block, dask_nodes, dask_ppn)

        submit_count = 0
        # Make sure any finished tasks are handled before attempting to submit
        # new ones
        self._wait_any_task(block=False)
        while True:
            if len(self.queued_tasks) == 0:
                break
            active_tasks = self.services.launch_task_pool(self.name, launch_interval)
            for task_name, task_id in active_tasks.items():
                self.active_tasks[task_id] = self.queued_tasks.pop(task_name)
                submit_count += 1
            if block:
                self._wait_any_task()
                continue
            else:
                return submit_count
        if block:
            self._wait_active_tasks()
        return submit_count

    def get_dask_finished_tasks_status(self):
        result = self.dask_client.gather(self.futures)
        self.dask_client.shutdown()
        self.dask_client.close()
        time.sleep(1)
        self.finished_tasks = {}
        self.active_tasks = {}
        self.services.wait_task(self.dask_workers_tid)
        self.dask_file_name = None
        self.dask_workers_tid = None
        self.dask_sched_pid = None
        self.dask_pool = False
        self.serial_pool = True
        return dict(result)

    def get_finished_tasks_status(self):
        """
        Return a dictionary of exit status values for all tasks that have
        finished since the last time finished tasks were polled.
        """
        if self.dask_pool:
            return self.get_dask_finished_tasks_status()
        if len(self.active_tasks) + len(self.finished_tasks) == 0:
            raise Exception('No more active tasks in task pool %s' % self.name)

        exit_status = {}
        self._wait_any_task()
        for task_name in list(self.finished_tasks.keys()):
            task = self.finished_tasks.pop(task_name)
            exit_status[task_name] = task.exit_status
        return exit_status

    def terminate_tasks(self):
        """
        Kill all active tasks, clear all queued, blocked and finished tasks.
        """
        if len(self.active_tasks) > 0:
            if self.dask_pool:
                _ = [f.cancel() for f in self.futures]
                self.futures = []
            else:
                for task_id in list(self.active_tasks.keys()):
                    self.services.kill_task(task_id)
        self.queued_tasks = {}
        self.blocked_tasks = {}
        self.active_tasks = {}
        self.finished_tasks = {}


class Task:
    r"""
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
        self.args = [str(a) for a in args] if args else args
        self.keywords = keywords
        self.exit_status = None
