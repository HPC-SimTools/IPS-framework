# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""IPS Services"""
import sys
import queue
import os
import subprocess
import threading

import time
import shutil
import logging
import logging.handlers
import signal
import glob
import json
import weakref
import inspect
from operator import itemgetter
from . import messages, ipsutil, component
from .configobj import ConfigObj
from .cca_es_spec import initialize_event_service
from .ips_es_spec import eventManager


def launch(binary, task_name, working_dir, *args, **keywords):
    """This is used by
    :meth:`TaskPool.submit_dask_tasks` as the
    input to :meth:`dask.distributed.Client.submit`.

    """
    from dask.distributed import get_worker  # pylint: disable=import-outside-toplevel

    worker = get_worker()
    if not hasattr(worker, 'lock'):
        worker.lock = threading.Lock()

    worker_name = ''.join(c for c in get_worker().name if c.isalnum())

    start_time = time.time()
    os.chdir(working_dir)

    worker_event_log = sys.stdout
    try:
        event_logfile = keywords["worker_event_logfile"].format(worker_name)
    except (KeyError, AttributeError):
        pass
    else:
        worker_event_log = open(event_logfile, 'a')

    ret_val = None
    if isinstance(binary, str):
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
            except OSError:
                pass

        task_env = keywords.get("task_env", {})
        new_env = os.environ.copy()
        new_env.update(task_env)

        timeout = float(keywords.get("timeout", 1.e9))

        cmd = f"{binary} {' '.join(map(str, args))}"
        with worker.lock:
            print(json.dumps({"event_type": "IPS_LAUNCH_DASK_TASK", "event_time": time.time(),
                              "event_comment": f"task_name = {task_name}, Target = {cmd}"}),
                  file=worker_event_log)

        cmd_lst = cmd.split()
        process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                   stderr=task_stderr,
                                   cwd=working_dir,
                                   preexec_fn=os.setsid,
                                   env=new_env)
        try:
            ret_val = process.wait(timeout)
            finish_time = time.time()
            with worker.lock:
                print(json.dumps({"event_type": "IPS_TASK_END", "event_time": finish_time,
                                  "event_comment": f"task_name = {task_name}, elasped time = {finish_time - start_time:.2f}s"}),
                      file=worker_event_log)
        except subprocess.TimeoutExpired:
            with worker.lock:
                print(json.dumps({"event_type": "IPS_TASK_END", "event_time": time.time(),
                                  "event_comment": f"task_name = {task_name}, timed-out after {timeout}s"}),
                      file=worker_event_log)
            os.killpg(process.pid, signal.SIGKILL)
            ret_val = -1
    else:
        with worker.lock:
            print(json.dumps({"event_type": "IPS_LAUNCH_DASK_TASK", "event_time": time.time(),
                              "event_comment": f"task_name = {task_name}, Target = {binary.__name__}({','.join(map(str, args))})"}),
                  file=worker_event_log)
        ret_val = binary(*args)
        finish_time = time.time()
        with worker.lock:
            print(json.dumps({"event_type": "IPS_TASK_END", "event_time": finish_time,
                              "event_comment": f"task_name = {task_name}, elasped time = {finish_time - start_time:.2f}s"}),
                  file=worker_event_log)

    return task_name, ret_val


class ServicesProxy:
    """The *ServicesProxy* object is responsible for marshalling
    invocations of framework services to the framework process using a
    shared queue.  The queue is shared among all components in a
    simulation. The results from framework services invocations are
    received via another, component-specific "framework response"
    queue.

    Create a new ServicesProxy object

    :param fwk: Enclosing IPS simulation framework
    :type fwk: :class:`ipsframework.ips.Framework`

    :param fwk_in_q: Framework input message queue - shared among all
                service objects
    :type fwk_in_q: :class:`multiprocessing.Queue`

    :param svc_response_q: Service response message queue - one per
                      service object.
    :type svc_response_q: :class:`multiprocessing.Queue`

    :param sim_conf: Simulation configuration dictionary, contains
                data from the simulation configuration file merged
                with the platform configuration file.
    :type sim_conf: dict

    :param log_pipe_name: Name of logging pipe for use by the IPS
                     logging daemon.
    :type log_pipe_name: str

    """

    def __init__(self, fwk, fwk_in_q, svc_response_q, sim_conf, log_pipe_name):
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
        except KeyError:
            try:
                log_level = self.sim_conf['LOG_LEVEL']
            except KeyError:
                pass
        try:
            real_log_level = getattr(logging, log_level)
        except AttributeError:
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
            self.shared_nodes = self.sim_conf['NODE_ALLOCATION_MODE'] == 'SHARED'

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
                if r.__class__ == messages.ServiceResponseMessage:
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
                            state='Running',
                            event_time=None):
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
        if event_time is None:
            event_time = time.time()
        portal_data['walltime'] = '%.2f' % (event_time - self.component_ref.start_time)
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
        :param port_name: port name
        :type port_name: str

        :return: Return a reference to the component implementing port *port_name*.
        :rtype: :class:`ipsframework.componentRegistry.ComponentID`
        """
        msg_id = self._invoke_service(self.fwk.component_id,
                                      'get_port', port_name)
        response = self._get_service_response(msg_id, True)
        return response

    def cleanup(self):
        """Clean up any state from the services. Called by the terminate
        method in the base class for components.

        """
        for (p, _, _) in self.task_map.values():
            try:
                p.kill()
            except Exception:
                pass

    def call_nonblocking(self, component_id, method_name, *args, **keywords):
        r"""Invoke method *method_name* on component *component_id* with
        optional arguments *\*args*. Will not wait until finished.

        :param component_id: Component ID of requested component
        :type component_id: :class:`~ipsframework.componentRegistry.ComponentID`

        :param method_name: component method to call, e.g. ``init`` or ``step``
        :type method_name: str

        :return: call_id
        :rtype: int
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
        r"""Invoke method *method_name* on component *component_id* with
        optional arguments *\*args*. Will wait until call is
        finished. Return result from invoking the method.

        :param component_id: Component ID of requested component
        :type component_id: :class:`~ipsframework.componentRegistry.ComponentID`

        :param method_name: component method to call, e.g. ``init`` or ``step``
        :type method_name: str

        :return: service response message arguments

        """
        call_id = self.call_nonblocking(component_id, method_name, *args, **keywords)
        retval = self.wait_call(call_id, block=True)
        return retval

    def wait_call(self, call_id, block=True):
        """If *block* is ``True``, return when the call has completed with
        the return code from the call.  If *block* is ``False``, raise
        :exc:`~ipsframework.ipsExceptions.IncompleteCallException` if
        the call has not completed, and the return value is it has.

        :param call_id: call ID
        :type call_id: int

        :return: service response message arguments

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
        """Check the status of each of the call in *call_id_list*.  If
        *block* is ``True``, return when *all* calls are finished.  If
        *block* is ``False``, raise
        :exc:`~ipsframework.ipsExceptions.IncompleteCallException` if
        *any* of the calls have not completed, otherwise return.  The
        return value is a dictionary of *call_ids* and return values.

        :param call_id_list: list of call ID's
        :type call_id_list: list of int

        :return: dict of call_id and return value
        :rtype: dict

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
        the task (:exc:`~ipsframework.ipsExceptions.InsufficientResourcesException`), bad
        task launch request
        (:exc:`~ipsframework.ipsExceptions.ResourceRequestMismatchException`,
        :exc:`~ipsframework.ipsExceptions.BadResourceRequestException`) or problems
        executing the command. These exceptions may be used to retry launching
        the task as appropriate.

        .. note :: This is a nonblocking function, users must use a version of :py:meth:`ServicesProxy.wait_task` to get result.

        :param nproc: number of processes
        :type nproc: int

        :param working_dir: change to this directory before launching task
        :type working_dir: str

        :param binary: command to execute, can include arguments or can be pass in with *\*args*
        :type binary: str

        :return: task_id (PID)
        :rtype: int

        """
        if not isinstance(binary, str):
            self.exception('Error in launch_task: task binary of wrong type, expected str but found %s', type(binary).__name__)
            raise ValueError(f"task binary of wrong type, expected str but found {type(binary).__name__}")

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

        task_ppn = keywords.get('task_ppn', self.ppn)
        block = keywords.get('block', True)
        tag = keywords.get('tag', 'None')

        whole_nodes = keywords.get('whole_nodes', not self.shared_nodes)
        whole_socks = keywords.get('whole_sockets', not self.shared_nodes)

        try:
            # SIMYAN: added working_dir to component method invocation
            msg_id = self._invoke_service(self.fwk.component_id,
                                          'init_task', nproc, binary_fullpath,
                                          working_dir, task_ppn, block,
                                          whole_nodes, whole_socks, *args)
            (task_id, command, env_update) = self._get_service_response(msg_id, block=True)
        except Exception:
            raise

        log_filename = keywords.get('logfile')
        timeout = keywords.get("timeout", 1.e9)

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

    def launch_task_pool(self, task_pool_name, launch_interval=0.0):
        """Construct messages to task manager to launch each task in task
        pool.  Used by :py:class:`TaskPool` to launch tasks in a
        task_pool.

        :param task_pool_name: name of task pool
        :type task_pool_name: str

        :param launch_internal: time to wait between launching tasks, default 0.0
        :type launch_internal: float

        :return: activate task, dictionary mapping task_name to task_id
        :rtype: dict
        """

        task_pool = self.task_pools[task_pool_name]
        queued_tasks = task_pool.queued_tasks
        submit_dict = {}
        for (task_name, task) in queued_tasks.items():
            if not isinstance(task.binary, str):
                self.exception('Error initiating task pool %s: task %s binary of wrong type, expected str but found %s',
                               task_pool_name, task_name, type(task.binary).__name__)
                raise ValueError(f"task {task_name} binary of wrong type, expected str but found {type(task.binary).__name__}")
            task_ppn = task.keywords.get('task_ppn', self.ppn)
            wnodes = task.keywords.get('whole_nodes', not self.shared_nodes)
            wsocks = task.keywords.get('whole_sockets', not self.shared_nodes)
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
            task = queued_tasks[task_name]
            (task_id, command, env_update) = allocated_tasks[task_name]

            tag = task.keywords.get('tag', 'None')

            log_filename = task.keywords.get('logfile')

            timeout = task.keywords.get("timeout", 1.e9)

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
        """Kill launched task *task_id*.  Return if successful.  Raises
        exceptions if the task or process cannot be found or killed
        successfully.

        :param task_id: task ID
        :type task_id: int

        :return: if successfully killed
        :rtype: bool
        """
        try:
            process, _, _ = self.task_map[task_id]
            # TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
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
        task_id_list = list(self.task_map)
        for task_id in task_id_list:
            try:
                self.kill_task(task_id)
            except Exception:
                raise

    def wait_task_nonblocking(self, task_id):
        """Check the status of task *task_id*.  If it has finished, the
        return value is populated with the actual value, otherwise
        ``None`` is returned.  A *KeyError* exception may be raised if
        the task is not found.

        :param task_id: task ID (PID)
        :type task_id: int

        :return: return value of task if finished else None
        """
        try:
            process, start_time, timeout = self.task_map[task_id]
            # TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
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

        :param task_id: task ID (PID)
        :type task_id: int

        :param timeout: maximum time to wait for task to finish, default -1 (no timeout)
        :type timeout: float

        :param delay: time to wait before checking if task has timed-out
        :type delay: float

        :return: return value of task
        """
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

    def wait_tasklist(self, task_id_list, block=True):
        """Check the status of a list of tasks.  If ``block`` is ``True``,
        return a dictionary of return values when *all* tasks have
        completed.  If ``block`` is ``False``, return a dictionary
        containing entries for each *completed* task.  Note that the
        dictionary may be empty.  Raise :class:`KeyError` exception if
        ``task_id`` not found.

        :param task_id_list: list of task_id's (PID's) to wait until completed
        :type task_id_list: list of int

        :param block: if to wait until all task finish
        :type block: bool

        :return: dict of task_id and return value
        :rtype: dict
        """
        ret_dict = {}
        running_tasks = list(task_id_list)
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
        Return the value of the configuration parameter ``param``.  Raise
        exception if not found and silent is False.

        :param param: The parameter requested from simulation config
        :type param: str

        :param silent: If True and parameter isn't found then exception is not raised, default False
        :type silent: bool

        :return: dictionary of given parameter from configuration
        :rtype: dict
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
        """Set configuration parameter *param* to *value*.  Raise exceptions
        if the parameter cannot be changed or if there are problems
        setting the value. This tell the framework to call
        :meth:`ipsframework.configurationManager.ConfigurationManager.set_config_parameter`
        to change the parameter.

        :param param: The parameter requested from simulation config
        :type param: str

        :param value: The value to set the parameter

        :return: return value from setting parameter

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

        :return: list of times
        :rtype: list of float
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
            Checkpint every time the call is made (equivalent to always setting
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
                if elapsed_time >= t > self.last_ckpt_walltime - self.start_time:
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
            try:
                pt_values = chkpt_conf['PHYSTIME_VALUES'].split()
            except AttributeError:
                pt_values = chkpt_conf['PHYSTIME_VALUES']
            pt_values = [float(t) for t in pt_values]
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

        :return: working directory
        :rtype: str
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

        File are copied using :func:`ipsframework.ipsutil.copyFiles`.

        :param input_file_list: input files can space separated string or iterable of strings
        :type input_file_list: str or Iterable of str
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
                input_target_dir = os.path.join(os.getcwd(), c)
                os.makedirs(input_target_dir, exist_ok=True)
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

    def stage_subflow_output_files(self, subflow_name='ALL'):
        """Gather outputs from sub-workflows. Sub-workflow output is defined
        to be the output files from its DRIVER component as they exist
        in the sub-workflow driver's work area at the end of the
        sub-simulation. If subflow_name != 'ALL' then get output from
        only that sub-flow

        """
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
            os.makedirs(plasma_dir, exist_ok=True)
        except OSError as e:
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
            os.makedirs(symlink_dir, exist_ok=True)
        except OSError as e:
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
                                          'merge_current_plasma_state', update_file,
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
                          event_comment="",
                          event_time=None):
        """
        Send event to web portal.
        """
        return self._send_monitor_event(eventType=event_type,
                                        comment=event_comment,
                                        event_time=event_time)

    def log(self, msg, *args):
        """
        Wrapper for :meth:`ServicesProxy.info`.
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
        self.logger.exception(msg, *args)

    def critical(self, msg, *args):
        """
        Produce **critical** message in simulation log file. See :func:`logging.critical` for usage.
        """
        self.logger.critical(msg, *args)

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
                     dask_ppn=None, launch_interval=0.0, use_shifter=False):
        """
        Launch all unfinished tasks in task pool *task_pool_name*.  If *block* is ``True``,
        return when all tasks have been launched.  If *block* is ``False``, return when all
        tasks that can be launched immediately have been launched.  Return number of tasks
        submitted.

        Optionally, dask can be used to schedule and run the task pool.
        """
        start_time = time.time()
        self._send_monitor_event('IPS_TASK_POOL_BEGIN', 'task_pool = %s ' % task_pool_name)
        task_pool: TaskPool = self.task_pools[task_pool_name]
        retval = task_pool.submit_tasks(block, use_dask, dask_nodes, dask_ppn, launch_interval, use_shifter)
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

    def create_sub_workflow(self, sub_name, config_file, override={}, input_dir=None):
        """Create sub-workflow

        """

        if sub_name in list(self.sub_flows.keys()):
            self.exception("Duplicate sub flow name")
            raise Exception("Duplicate sub flow name")

        self.subflow_count += 1
        try:
            sub_conf_new = ConfigObj(infile=config_file, interpolation='template', file_error=True)
            sub_conf_old = ConfigObj(infile=config_file, interpolation='template', file_error=True)
        except Exception:
            self.exception("Error accessing sub-workflow config file %s" % config_file)
            raise
        # Update undefined sub workflow configuration entries using top level configuration
        # only applicable to non-component entries (ones with non-dictionary values)
        for (k, v) in self.sim_conf.items():
            if k not in list(sub_conf_new.keys()) and type(v).__name__ != 'dict':
                sub_conf_new[k] = v

        sub_conf_new['SIM_NAME'] = self.sim_name + "::" + sub_name
        sub_conf_new['SIM_ROOT'] = os.path.join(os.getcwd(), sub_name)
        # sub_conf_new['SIM_ROOT'] = os.path.join(os.getcwd(), 'sub_workflow_%d' % self.subflow_count)
        # Update INPUT_DIR for components to current working dir (super simulation working dir)
        ports = sub_conf_new['PORTS']['NAMES'].split()
        comps = [sub_conf_new['PORTS'][p]['IMPLEMENTATION'] for p in ports]
        for c in comps:
            if not c:
                continue
            if input_dir is None:
                sub_conf_new[c]['INPUT_DIR'] = os.path.join(os.getcwd(), c)
            else:
                sub_conf_new[c]['INPUT_DIR'] = os.path.join(os.getcwd(), input_dir)
            try:
                override_vals = override[c]
            except KeyError:
                pass
            else:
                for (k, v) in override_vals.items():
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
        """Create simulation"""
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
        distributed: dask.distributed = __import__("dask.distributed")
    except ImportError:
        dask = None
        distributed = None
    else:
        dask_scheduler = shutil.which("dask-scheduler")
        dask_worker = shutil.which("dask-worker")
        shifter = shutil.which("shifter")
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

        :param task_name: unique task name
        :type task_name: str
        :param nproc: number of process to run task with
        :type nproc: int
        :param working_dir: change to this directory before launching task
        :type working_dir: str
        :param binary: full path to executable to launch
        :type binary: str
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

        keywords['keywords']['block'] = False

        self.serial_pool = self.serial_pool and (nproc == 1)
        self.queued_tasks[task_name] = Task(task_name, nproc, working_dir, binary_fullpath, *args,
                                            **keywords["keywords"])

    def submit_dask_tasks(self, block=True, dask_nodes=1, dask_ppn=None, use_shifter=False):
        """Launch tasks in *queued_tasks* using dask.

        :param block: Unused, this will always return after tasks are submitted
        :type block: bool
        :param dask_nodes: Number of task nodes, default 1
        :type dask_nodes: int
        :param dask_ppn:  Number of processes per node, default None
        :type dask_ppn: int
        :param use_shifter:  Option to launch dask scheduler and workers in shifter container
        :type use_shifter: bool
        """
        services: ServicesProxy = self.services
        self.dask_file_name = os.path.join(os.getcwd(),
                                           f".{self.name}_dask_shed_{time.time()}.json")
        if use_shifter:
            self.dask_sched_pid = subprocess.Popen([self.shifter, "dask-scheduler", "--no-dashboard",
                                                    "--scheduler-file", self.dask_file_name, "--port", "0"]).pid
        else:
            self.dask_sched_pid = subprocess.Popen([self.dask_scheduler, "--no-dashboard",
                                                    "--scheduler-file", self.dask_file_name, "--port", "0"]).pid

        dask_nodes = 1 if dask_nodes is None else dask_nodes
        if services.get_config_param("MPIRUN") == "eval":
            dask_nodes = 1

        nthreads = dask_ppn if dask_ppn else services.get_config_param("PROCS_PER_NODE")
        if use_shifter:
            self.dask_workers_tid = services.launch_task(dask_nodes, os.getcwd(),
                                                         self.shifter,
                                                         "dask-worker",
                                                         "--scheduler-file",
                                                         self.dask_file_name,
                                                         "--nprocs", 1,
                                                         "--nthreads", nthreads,
                                                         "--no-dashboard",
                                                         "--preload", self.services.dask_preload,
                                                         task_ppn=1)
        else:
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

        try:
            self.worker_event_logfile = services.sim_name + '_' + services.get_config_param("PORTAL_RUNID") + '_' + self.name + '_{}.json'
        except KeyError:
            # USE_PORTAL == False
            self.worker_event_logfile = None

        launch.__module__ = "__main__"
        self.futures = []
        for task_name, task in self.queued_tasks.items():
            self.futures.append(self.dask_client.submit(launch,
                                                        task.binary,
                                                        task_name,
                                                        task.working_dir,
                                                        *task.args,
                                                        **task.keywords,
                                                        worker_event_logfile=self.worker_event_logfile))
        self.active_tasks = self.queued_tasks
        self.queued_tasks = {}
        return len(self.futures)

    def submit_tasks(self, block=True, use_dask=False, dask_nodes=1, dask_ppn=None, launch_interval=0.0, use_shifter=False):
        """Launch tasks in *queued_tasks*.  Finished tasks are handled before
        launching new ones.  If *block* is ``True``, the number of
        tasks submitted is returned after all tasks have been launched
        and completed.  If *block* is ``False`` the number of tasks
        that can immediately be launched is returned.

        If ``use_dask==True`` then the tasks are launched with
        :meth:`submit_dask_tasks`.

        :param block: If True then wait for task to complete, default True
        :type block: bool
        :param use_dask: If True then use dask to launch tasks, default False
        :type use_dask: bool
        :param dask_nodes: Number of task nodes, only used it ``use_dask==True``
        :type dask_nodes: int
        :param dask_ppn:  Number of processes per node, only used it ``use_dask==True``
        :type dask_ppn: int
        :param launch_internal: time to wait between launching tasks, default 0.0
        :type launch_internal: float
        :param use_shifter:  Option to launch dask scheduler and workers in shifter container
        :type use_shifter: bool

        """

        if use_dask:
            if TaskPool.dask and self.serial_pool:
                self.dask_pool = True
                if use_shifter and not self.shifter:
                    self.services.exception("Requested to run dask within shifter but shifter not available")
                    raise Exception("shifter not found")
                else:
                    return self.submit_dask_tasks(block, dask_nodes, dask_ppn, use_shifter)
            elif not TaskPool.dask:
                self.services.warning("Requested use_dask but cannot because import dask failed")
            elif not self.serial_pool:
                self.services.warning("Requested use_dask but cannot because multiple processors requested")

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
        """Return a dictionary of exit status values for all dask tasks that
        have finished since the last time finished tasks were polled.

        :return: dict mapping task name to exit status
        :rtype: dict
        """
        result = self.dask_client.gather(self.futures)
        worker_names = [''.join(c for c in worker['name'] if c.isalnum()) for worker in self.dask_client.scheduler_info()['workers'].values()]
        self.dask_client.shutdown()
        self.dask_client.close()
        time.sleep(1)
        if self.worker_event_logfile is not None:
            try:
                events = []
                for worker in worker_names:
                    filename = self.worker_event_logfile.format(worker)
                    try:
                        lines = open(filename).readlines()
                    except IOError:
                        self.services.exception('Error opening dask worker log file: %s', filename)
                    else:
                        # convert to dict and sort by event_time
                        for line in lines:
                            try:
                                events.append(json.loads(line.strip()))
                            except json.decoder.JSONDecodeError:
                                self.services.exception('Error reading line %s from dask worker log file: %s', line.strip(), filename)

                events.sort(key=itemgetter('event_time'))
                for event in events:
                    self.services.send_portal_event(**event)
            except Exception as e:
                # If it fails for any other reason, make sure we can continue
                self.services.exception('Error while reading dask worker log files: %s', str(e))
            else:
                for worker in worker_names:
                    os.remove(self.worker_event_logfile.format(worker))

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

        :return: dict mapping task name to exit status
        :rtype: dict
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

    :param name: task name
    :type name: str
    :param nproc: number of processes the task needs
    :type nproc: int
    :param working_dir: location to launch task from
    :type working_dir: str
    :param binary: full path to executable to launch
    :type binary: str
    :param \*args: arguments for *binary*
    :param \*\*keywords: keyword arguments for launching the task.  See :py:meth:`ServicesProxy.launch_task` for details.
    """

    def __init__(self, task_name, nproc, working_dir, binary, *args, **keywords):
        self.name = task_name
        self.nproc = int(nproc)
        self.working_dir = working_dir
        self.binary = binary
        self.args = [str(a) for a in args] if args else args
        self.keywords = keywords
        self.exit_status = None
