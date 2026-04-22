# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""IPS Services"""

import functools
import glob
import hashlib
import json
import logging
import logging.handlers
from datetime import datetime
import os
import queue
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
import weakref
from copy import deepcopy
from multiprocessing import Queue
from operator import iadd, itemgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, NamedTuple, Optional, Union

from rich import pretty
pretty.install()

from rich.console import Console
console = Console()

import rich.traceback
from rich.traceback import Traceback
rich.traceback.install(show_locals=True)

from configobj import ConfigObj
from distributed import Client, Worker, WorkerPlugin

from ipsframework import ipsutil, messages
from ipsframework.cca_es_spec import initialize_event_service
from ipsframework.componentRegistry import ComponentID
from ipsframework.ips_es_spec import eventManager
from ipsframework.taskManager import TaskInit

if TYPE_CHECKING:
    from ipsframework.component import Component


class RunningTask(NamedTuple):
    process: subprocess.Popen[bytes]
    start_time: float
    timeout: float
    nproc: int
    cores_allocated: int
    command: str
    binary: str
    args: list[str]


def launch(binary: Any, task_name: str, working_dir: Union[str, os.PathLike], *args, **keywords):
    """This is used by
    :meth:`TaskPool.submit_dask_tasks` as the
    input to :meth:`dask.distributed.Client.submit`.

    Valid keywords:
    * `worker_event_logfile` - where JSON log messages are written
    * `logfile` - where the task output is written; if not specified, STDOUT used
    * `errfile` - where the task error output is written; if not specified, STDOUT used
    * `task_env` - A dictionary of environment variables to set
    * `timeout` - The timeout in seconds for the task to complete.
    * `cpus_per_proc` - The number of cpus per process to use for the task. This implies that the DVMPlugin has set up a DVM daemon for this node.
    * `oversubscribe` - If `True`, then the number of processes can exceed the number of cores on the node.  Default is `False`.

    If the worker has the attribute `dvm_uri_file`, then we are running
    with a DVM (Distributed Virtual Machine) so the `binary` needs a
    `prun` prepended pointing to that.

    If the worker doesn't have a `lock` attribute, then we create one by
    assigning a threading lock to it. This is used to ensure that
    the worker's event log is written to in a thread-safe manner.

    :param binary: The binary to launch. Either a string or a class.
    :param task_name: The name of the task.
    :param working_dir: The working directory in which to run this task
    :returns: The task name and the return value from running the binary.
    """
    from dask.distributed import get_worker  # pylint: disable=import-outside-toplevel

    worker = get_worker()
    if not hasattr(worker, 'lock'):
        worker.lock = threading.Lock()

    worker_name = ''.join(c for c in worker.name if c.isalnum())

    worker.logger.info(f'Launching task {task_name} with worker {worker_name} in {working_dir}')

    start_time = time.time()
    os.chdir(working_dir)

    worker_event_log = sys.stdout
    try:
        event_logfile = keywords['worker_event_logfile'].format(worker_name)
    except (KeyError, AttributeError):
        worker.logger.warning('No worker_event_logfile specified, using stdout for logging')
    else:
        worker_event_log = open(event_logfile, 'a')
        worker.logger.info(f'Worker event log file: {event_logfile}')

    ret_val = None
    if isinstance(binary, str):
        task_stdout = sys.stdout
        try:
            log_filename = keywords['logfile']
        except KeyError:
            worker.logger.info('No logfile specified, using stdout for task output')
        else:
            task_stdout = open(log_filename, 'w')
            worker.logger.info(f'Task output log file: {log_filename}')

        task_stderr = subprocess.STDOUT
        try:
            err_filename = keywords['errfile']
        except KeyError:
            worker.logger.info('No errfile specified, using STDOUT for task errors')
        else:
            try:
                task_stderr = open(err_filename, 'w')
            except OSError:
                worker.logger.info(f'Could not open errfile {err_filename}, using STDOUT for task errors')
                task_stderr = subprocess.STDOUT
            else:
                worker.logger.info(f'Task error log file: {err_filename}')

        task_env = keywords.get('task_env', {})
        new_env = os.environ.copy()
        new_env.update(task_env)

        if 'HWLOC_XMLFILE' in new_env:
            worker.logger.debug('Removing HWLOC_XMLFILE from task environment')
            del new_env['HWLOC_XMLFILE']

        # Check that the DVM environment variables are set.
        if hasattr(worker, 'dvm_uri_file'):
            dvm_uri_file = Path(worker.dvm_uri_file)
            if not dvm_uri_file.exists():
                worker.logger.error(f'DVM URI file {dvm_uri_file} does not exist')
                print(f'DVM URI file {dvm_uri_file} does not exist', flush=True)
            else:
                worker.logger.debug(f'Using DVM URI file: {dvm_uri_file}')
                print(f'Using DVM URI file: {dvm_uri_file}', flush=True)

        # PMIX_SERVER_URI41 is used by prun to figure out how to talk to the DVM
        # It can be defined in `task_env` or in `os.environ`, so we look in
        # both locations to just echo its presence. The flushes are necessary
        # in some HPC environments to ensure the output appears in the logs.
        if task_env is not None and task_env != {}:
            if 'PMIX_SERVER_URI41' in task_env:
                worker.logger.debug(f"DVM environment variable PMIX_SERVER_URI41 "
                                   f"set in task_env to "
                                   f"{task_env['PMIX_SERVER_URI41']}")
                print(f'DVM environment variable PMIX_SERVER_URI41 set in task_'
                      f'env to {task_env["PMIX_SERVER_URI41"]}', flush=True)
        if 'PMIX_SERVER_URI41' in os.environ:
            worker.logger.debug(f"DVM environment variable PMIX_SERVER_URI41 set "
                               f"in os.environ to "
                               f"{os.environ['PMIX_SERVER_URI41']}")
            print(f'DVM environment variable PMIX_SERVER_URI41 set in os.environ '
                  f'to {os.environ["PMIX_SERVER_URI41"]}', flush=True)

        timeout = float(keywords.get('timeout', 1.0e9))

        cmd = f'{binary} {" ".join(map(str, args))}'

        worker.logger.debug(f'Launching task {task_name} with command: {cmd}')

        with worker.lock:
            print(
                json.dumps({'eventType': 'IPS_LAUNCH_DASK_TASK', 'event_time': time.time(), 'comment': f'task_name = {task_name}, Target = {cmd}'}),
                file=worker_event_log,
            )

        cmd_lst = cmd.split()
        try:
            process = subprocess.Popen(cmd_lst, stdout=task_stdout,
                                       stderr=task_stderr,
                                       cwd=working_dir,
                                       preexec_fn=os.setsid, env=new_env)  # noqa: PLW1509 (TODO: look into this to potentially avoid deadlocks)
        except Exception as e:
            with worker.lock:
                print(
                    json.dumps(
                        {
                            'eventType': 'IPS_TASK_END',
                            'event_time': time.time(),
                            'comment': f'task_name = {task_name} Exception when calling {binary!s}: {e}',
                            'operation': ' '.join(map(str, args)),
                        }
                    ),
                    file=worker_event_log,
                )
            worker.logger.error(f'Failed to launch task {task_name} with command {cmd}: {e}')
            raise

        try:
            ret_val = process.wait(timeout)
            finish_time = time.time()
            with worker.lock:
                print(
                    json.dumps(
                        {
                            'eventType': 'IPS_TASK_END',
                            'event_time': finish_time,
                            'comment': f'task_name = {task_name}, elapsed time = {finish_time - start_time:.2f}s',
                            'start_time': start_time,
                            'elapsed_time': finish_time - start_time,
                            'target': binary,
                            'operation': ' '.join(map(str, args)),
                        }
                    ),
                    file=worker_event_log,
                )
        except subprocess.TimeoutExpired:
            with worker.lock:
                print(
                    json.dumps({'eventType': 'IPS_TASK_END', 'event_time': time.time(), 'comment': f'task_name = {task_name}, timed-out after {timeout}s'}),
                    file=worker_event_log,
                )
            os.killpg(process.pid, signal.SIGKILL)
            worker.logger.error(f'Task {task_name} with command {cmd} timed out after {timeout}s')
            ret_val = -1
        except Exception as e:
            with worker.lock:
                print(
                    json.dumps(
                        {'eventType': 'IPS_TASK_END', 'event_time': time.time(), 'comment': f'task_name = {task_name} Exception when calling {binary!s}: {e}'}
                    ),
                )
            worker.logger.error(f'Task {task_name} with command {cmd} failed with {e}')
    else:
        with worker.lock:
            print(
                json.dumps(
                    {
                        'eventType': 'IPS_LAUNCH_DASK_TASK',
                        'event_time': time.time(),
                        'comment': f'task_name = {task_name}, Target = {binary.__name__}({",".join(map(str, args))})',
                    }
                ),
                file=worker_event_log,
            )
        ret_val = binary(*args)
        finish_time = time.time()
        with worker.lock:
            print(
                json.dumps(
                    {
                        'eventType': 'IPS_TASK_END',
                        'event_time': finish_time,
                        'comment': f'task_name = {task_name}, elapsed time = {finish_time - start_time:.2f}s',
                        'start_time': start_time,
                        'elapsed_time': finish_time - start_time,
                        'target': binary.__name__,
                        'return_value': ret_val,
                        'operation': f'({",".join(map(str, args))})',
                    }
                ),
                file=worker_event_log,
            )

    worker.logger.info(f'Task {task_name} finished with return value: {ret_val}')

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

    def __init__(self, fwk, fwk_in_q: Queue, svc_response_q: Queue, sim_conf: dict[str, Any], log_pipe_name: str):
        self.pid = 0
        self.fwk = fwk
        self.fwk_in_q = fwk_in_q
        self.svc_response_q = svc_response_q
        self.sim_conf = sim_conf
        self.log_pipe_name = log_pipe_name
        self.component_ref: Component = None  # type: ignore
        self.incomplete_calls = {}
        self.finished_calls = {}
        self.task_map: dict[int, RunningTask] = {}
        self.workdir = ''
        self.full_comp_id = ''
        self.logger: logging.Logger = None  # type: ignore
        self.start_time = time.time()
        self.cur_time = self.start_time
        self.event_service = None
        self.counter = 0
        self.monitor_url = ''
        self.call_targets = {}
        self.task_pools: dict[str, TaskPool] = {}
        self.time_loop = None
        self.last_ckpt_walltime = self.start_time
        self.last_ckpt_phystime = None
        self.new_chkpts = []
        self.protected_chkpts = []
        self.chkpt_counter = 0
        self.sim_name = ''
        self.replay_conf = None
        self.subflow_count = 0
        self.sub_flows = {}
        self.binary_fullpath_cache = {}
        self.ppn = 0
        self.cpp = 0
        self.shared_nodes = False
        self._portal_runid = -1
        """This is the id we use on the portal to track this specific run. This will get set when receiving the IPS_START event from the portal.
        
        - Non-negative integer = successfully initialized
        - -1 = portal not yet contacted
        - -2 = portal initialization failed
        """
        self._fallback_portal_runid = str(uuid.uuid4())
        """
        This is meant to be a unique identifier fallback in the event we can't get the portal runid.
        """
        self._portal_runid_event = threading.Event()
        """Thread-safe means to detect if self._portal_runid has been set"""

    def __initialize__(self, component_ref):
        """
        Initialize the service proxy object, connecting it to its associated
        component.

        This method is for use only by the IPS framework.
        """

        self.component_ref = weakref.proxy(component_ref)
        conf = self.component_ref.config
        self.full_comp_id = '_'.join([conf['CLASS'], conf['SUB_CLASS'], conf['NAME'], str(self.component_ref.component_id.get_seq_num())])
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
        self.debug('__initialize__(): %s  %s ', str(self.component_ref), str(self.component_ref.component_id))
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
                self.fwk.error("Bad 'NODE_ALLOCATION_MODE' value %s", pn_compconf)
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

        try:
            self.cpp = int(conf['CPUS_PER_PROC'])
        except Exception:
            self.cpp = 0

        if self.sim_conf['SIMULATION_MODE'] == 'RESTART':
            if self.sim_conf['RESTART_TIME'] == 'LATEST':
                chkpts = glob.glob(os.path.join(self.sim_conf['RESTART_ROOT'], 'restart', '*'))
                base_dir = sorted(chkpts, key=lambda d: float(os.path.basename(d)))[-1]
                self.sim_conf['RESTART_TIME'] = os.path.basename(base_dir)

    def _init_event_service(self) -> None:
        """
        Initialize connection to the central framework event service
        """
        self.debug('_init_event_service(): self.counter = %d - %s', self.counter, str(self.component_ref))
        self.counter = self.counter + 1
        initialize_event_service(self)
        self.event_service = eventManager(self.component_ref)

    def _get_elapsed_time(self) -> float:
        """
        Return total elapsed time since simulation started in seconds
        (including a possible fraction)
        """
        self.cur_time = time.time()
        delta_t = self.cur_time - self.start_time
        return delta_t

    def _get_incoming_responses(self, block: bool = False) -> list[Any]:
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
        try:
            return self.finished_calls.pop(msg_id)
        except KeyError:
            if msg_id not in self.incomplete_calls:
                self.error('Invalid call ID : %s ', str(msg_id))
                raise Exception('Invalid message request ID argument') from None

        keep_going = True
        while keep_going:
            # get new messages, block until something interesting comes along
            responses = self._get_incoming_responses(block)
            for r in responses:
                if isinstance(r, messages.ServiceResponseMessage):
                    if r.request_msg_id not in self.incomplete_calls:
                        self.error('Mismatched service response msg_id %s', str(r.request_msg_id))
                        raise Exception('Mismatched service response msg_id.')
                    else:
                        del self.incomplete_calls[msg_id]
                        self.finished_calls[r.request_msg_id] = r
                        if r.request_msg_id == msg_id:
                            keep_going = False
                # some weird message came through
                else:
                    self.error('Unexpected service response of type %s', r.__class__.__name__)
                    #                    dumpAll()
                    raise Exception('Unexpected service response of type ' + r.__class__.__name__)

            if not block:
                keep_going = False
        # if this message corresponds to a finish invocation, return the response message
        return self.finished_calls.pop(msg_id, None)

    def _invoke_service(self, component_id: ComponentID, method_name: str, *args, **keywords):
        """Call a method for the given component

        Create and place in the ``self.fwk_in_q`` a new
        :py:meth:`messages.ServiceRequestMessage` for service `method_name`
        with `args` arguments on behalf of component `component_id`.  Return
        message id.

        :param component_id: Component ID of requested component
        :param method_name: component method to call, e.g. ``init`` or ``step``
        :return: message id
        """
        self.debug('_invoke_service(): %s  %s', method_name, str(args[0:]))
        new_msg = messages.ServiceRequestMessage(self.component_ref.component_id, self.fwk.component_id, component_id, method_name, *args, **keywords)
        msg_id = new_msg.get_message_id()
        self.incomplete_calls[msg_id] = new_msg
        self.fwk_in_q.put(new_msg)
        return msg_id

    def _get_service_response(self, msg_id, block=True):
        """
        Return response from message `msg_id`.  Calls
        :py:meth:`ServicesProxy._wait_msg_response` with `msg_id` and
        `block`.  If response is not present, `None` is returned, otherwise
        the response is passed on to the component.  If the status of the
        response is failure (`Message.FAILURE`), then the exception body is
        raised.

        :param msg_id: message id
        :param block: Boolean flag. If ``True``, block waiting for one or more
            responses to arrive.
        :return: response arguments
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

    def _send_monitor_event(
        self,
        eventType='',
        comment='',
        ok=True,
        state='Running',
        event_time=None,
        elapsed_time=None,
        start_time=None,
        end_time=None,
        target=None,
        operation=None,
        procs_requested=None,
        cores_allocated=None,
        call_id=0,
    ) -> None:
        """
        Construct and send an event populated with the component's
        information, *eventType*, *comment*, *ok*, *state*, and a wall time
        stamp, to the portal bridge to pass on to the web portal.
        """
        portal_data = {}
        portal_data['code'] = f'{self.component_ref.CLASS}_{self.component_ref.SUB_CLASS}_{self.component_ref.NAME}'
        portal_data['eventtype'] = eventType
        portal_data['ok'] = ok
        if event_time is None:
            event_time = time.time()
        portal_data['walltime'] = '%.2f' % (event_time - self.component_ref.start_time)
        portal_data['time'] = ipsutil.getTimeString(time.localtime(event_time))

        trace = {}  # Zipkin json format
        if start_time is not None and (elapsed_time is not None or end_time is not None) and target is not None and operation is not None:
            trace['timestamp'] = int(start_time * 1e6)  # convert to microsecond
            if elapsed_time is not None:
                trace['duration'] = int(elapsed_time * 1e6)
            elif end_time is not None:
                trace['duration'] = int((end_time - start_time) * 1e6)  # convert to microsecond
            trace['localEndpoint'] = {'serviceName': target}
            trace['name'] = operation
            formatted_args = ['%.3f' % (x) if isinstance(x, float) else str(x) for x in self.component_ref.args]
            trace['id'] = hashlib.md5(f'{target}:{operation}:{call_id}'.encode()).hexdigest()[:16]
            trace['parentId'] = hashlib.md5(
                f'{self.component_ref.component_id}:{self.component_ref.method_name}({" ,".join(formatted_args)}):{self.component_ref.call_id}'.encode()
            ).hexdigest()[:16]
            trace['tags'] = {}
            if procs_requested is not None:
                trace['tags']['procs_requested'] = str(procs_requested)
            if cores_allocated is not None:
                trace['tags']['cores_allocated'] = str(cores_allocated)

        if trace:
            portal_data['trace'] = trace

        portal_data['state'] = state
        portal_data['comment'] = comment
        if self.monitor_url:
            portal_data['vizurl'] = self.monitor_url.split('//')[-1]

        event_data = {}
        event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
        event_data['real_sim_name'] = self.sim_name
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTAL_EVENT', event_data)

    def get_port(self, port_name: str) -> ComponentID:
        """
        :param port_name: port name
        :type port_name: str

        :return: Return a reference to the component implementing port *port_name*.
        :rtype: :class:`ipsframework.componentRegistry.ComponentID`
        """
        msg_id = self._invoke_service(self.fwk.component_id, 'get_port', port_name)
        response = self._get_service_response(msg_id, True)
        return response

    def cleanup(self):
        """Clean up any state from the services. Called by the terminate
        method in the base class for components.

        """
        for task in self.task_map.values():
            try:
                task.process.kill()
            except Exception:
                pass

    def call_nonblocking(self, component_id: ComponentID, method_name: str, *args, **keywords) -> int:
        r"""Invoke method *method_name* on component *component_id* with
        optional arguments *\*args*. Will not wait until finished.

        :param component_id: Component ID of requested component
        :type component_id: :class:`~ipsframework.componentRegistry.ComponentID`

        :param method_name: component method to call, e.g. ``init`` or ``step``
        :type method_name: str

        :return: call_id
        :rtype: int
        """
        target = str(component_id)
        formatted_args = ['%.3f' % (x) if isinstance(x, float) else str(x) for x in args]
        if keywords:
            formatted_args += ['%s=' % k + str(v) for (k, v) in keywords.items()]
        self._send_monitor_event('IPS_CALL_BEGIN', 'Target = ' + target + ':' + method_name + '(' + ' ,'.join(formatted_args) + ')')
        msg_id = self._invoke_service(component_id, 'init_call', method_name, *args, **keywords)
        call_id = self._get_service_response(msg_id, True)
        self.call_targets[call_id] = (target, method_name, args, time.time())
        return call_id

    def call(self, component_id: ComponentID, method_name: str, *args, **keywords):
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

    def wait_call(self, call_id: int, block: bool = True):
        """If *block* is ``True``, return when the call has completed with
        the return code from the call.  If *block* is ``False``, raise
        :exc:`~ipsframework.ipsExceptions.IncompleteCallException` if
        the call has not completed, and the return value is it has.

        :param call_id: call ID
        :type call_id: int

        :return: service response message arguments

        """
        try:
            (target, method_name, args, start_time) = self.call_targets[call_id]
        except KeyError:
            self.exception('Invalid call_id in wait-call() : %s', call_id)
            raise
        msg_id = self._invoke_service(self.fwk.component_id, 'wait_call', call_id, block)
        formatted_args = ','.join('%.3f' % (x) if isinstance(x, float) else str(x) for x in args)
        target_full = f'{target}:{method_name}({formatted_args})'
        try:
            response = self._get_service_response(msg_id, block=True)
            self._send_monitor_event(
                'IPS_CALL_END',
                'Target = ' + target_full,
                start_time=start_time,
                end_time=time.time(),
                elapsed_time=time.time() - start_time,
                target=target,
                operation=f'{method_name}({formatted_args})',
                call_id=call_id,
            )
        except Exception as e:
            self._send_monitor_event(
                'IPS_CALL_END',
                f'Error: "{e}" Target = {target_full}',
                start_time=start_time,
                end_time=time.time(),
                elapsed_time=time.time() - start_time,
                target=target,
                operation=f'{method_name}({formatted_args})',
                call_id=call_id,
                ok=False,
            )
            raise

        del self.call_targets[call_id]
        return response

    def wait_call_list(self, call_id_list: list[int], block=True):
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

    def launch_task(self, nproc: int, working_dir: str, binary: str, *args, **keywords) -> int:
        r"""
        Launch *binary* in *working_dir* on *nproc* processes.  *\*args* are
        any arguments to be passed to the binary on the command line.
        *\*\*keywords* are any keyword arguments used by the framework to
        manage how the binary is launched.  Keywords may be the following:

            * *task_ppn* : the processes per node value for this task
            * *task_cpp* : the cores per process, only used when ``MPIRUN=srun`` commands
            * *task_gpp* : the gpus per process, only used when ``MPIRUN=srun`` commands
            * *omp* : If ``True`` the task will be launch with the correct OpenMP environment
               variables set, only used when ``MPIRUN=srun``
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
            * *launch_cmd_extra_args* : extra command arguments added the the MPIRUN command

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
            self.error('Error in launch_task: task binary of wrong type, expected str but found %s', type(binary).__name__)
            raise ValueError(f'task binary of wrong type, expected str but found {type(binary).__name__}')

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
            self.error('Program %s is not in path or is not executable', binary)
            raise Exception('Program %s is not in path or is not executable' % binary)
        else:
            self.binary_fullpath_cache[binary] = binary_fullpath

        task_ppn = keywords.get('task_ppn', self.ppn)
        task_cpp = keywords.get('task_cpp', self.cpp)
        task_gpp = keywords.get('task_gpp', 0)
        omp = keywords.get('omp', False)
        block = keywords.get('block', True)
        tag = keywords.get('tag', 'None')
        launch_cmd_extra_args = keywords.get('launch_cmd_extra_args')

        whole_nodes = keywords.get('whole_nodes', not self.shared_nodes)
        whole_socks = keywords.get('whole_sockets', not self.shared_nodes)

        self.debug(f'task_ppn = {task_ppn}')
        self.debug(f'task_cpp = {task_cpp}')
        self.debug(f'task_gpp = {task_gpp}')
        self.debug(f'omp = {omp}')
        self.debug(f'tag = {tag}')
        self.debug(f'launch_cmd_extra_args = {launch_cmd_extra_args}')
        self.debug(f'whole_nodes = {whole_nodes}')
        self.debug(f'whole_socks = {whole_socks}')

        task_id = command = env_update = cores_allocated = None

        try:
            # SIMYAN: added working_dir to component method invocation
            msg_id = self._invoke_service(
                self.fwk.component_id,
                'init_task',
                TaskInit(
                    int(nproc),
                    binary_fullpath,
                    working_dir,
                    int(task_ppn),
                    task_cpp,
                    task_gpp,
                    block,
                    omp,
                    whole_nodes,
                    whole_socks,
                    args,
                    launch_cmd_extra_args,
                ),
            )
            (task_id, command, env_update, cores_allocated) = self._get_service_response(msg_id, block=True)
            self.debug(f'init_task(): task_id = {task_id}')
            self.debug(f'command = {command}')
            self.debug(f'env_update = {env_update}')
            self.debug(f'cores_allocated = {cores_allocated}')
        except Exception as e:
            self.error(f'Error setting up task for command "{command}": {e}')
            raise

        task_id = self._launch_task(nproc, working_dir, task_id, command, cores_allocated, env_update, tag, keywords, binary, args)

        self.debug(f'Returned task_id = {task_id} for launching "{command}"')

        if env_update:
            self._send_monitor_event(
                'IPS_LAUNCH_TASK',
                f'task_id = {task_id} , Tag = {tag} , nproc = {nproc} , Target = {command}, env = {env_update}',
                procs_requested=nproc,
                cores_allocated=cores_allocated,
            )
        else:
            self._send_monitor_event(
                'IPS_LAUNCH_TASK',
                f'task_id = {task_id} , Tag = {tag} , nproc = {nproc} , Target = {command}',
                procs_requested=nproc,
                cores_allocated=cores_allocated,
            )

        return task_id

    def _launch_task(
        self, nproc: int, working_dir: str, task_id, command, cores_allocated, env_update, tag, keywords, binary: str, args: Union[list[str], tuple[str, ...]]
    ):
        log_filename = keywords.get('logfile')
        timeout = keywords.get('timeout', 1.0e9)

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
                new_env = os.environ.copy()
                new_env.update(env_update)
                process = subprocess.Popen(cmd_lst, stdout=task_stdout, stderr=task_stderr, cwd=working_dir, env=new_env)
            else:
                process = subprocess.Popen(cmd_lst, stdout=task_stdout, stderr=task_stderr, cwd=working_dir)
        except Exception:
            self.exception('Error executing command : %s', command)
            raise

        # FIXME: process Monitoring Command : ps --no-headers -o pid,state pid1  pid2 pid3 ...

        self.task_map[task_id] = RunningTask(process, time.time(), timeout, nproc, cores_allocated, command, binary, args)
        return task_id  # process.pid

    def launch_task_pool(self, task_pool_name: str, launch_interval: float = 0.0) -> dict[str, Any]:
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
        for task_name, task in queued_tasks.items():
            if not isinstance(task.binary, str):
                self.error(
                    'Error initiating task pool %s: task %s binary of wrong type, expected str but found %s',
                    task_pool_name,
                    task_name,
                    type(task.binary).__name__,
                )
                raise ValueError(f'task {task_name} binary of wrong type, expected str but found {type(task.binary).__name__}')
            task_ppn = task.keywords.get('task_ppn', self.ppn)
            wnodes = task.keywords.get('whole_nodes', not self.shared_nodes)
            wsocks = task.keywords.get('whole_sockets', not self.shared_nodes)
            task_cpp = task.keywords.get('task_cpp', self.cpp)
            task_gpp = task.keywords.get('task_gpp', 0)
            omp = task.keywords.get('omp', False)
            launch_cmd_extra_args = task.keywords.get('launch_cmd_extra_args')
            submit_dict[task_name] = TaskInit(
                task.nproc, task.binary, task.working_dir, task_ppn, task_cpp, task_gpp, False, omp, wnodes, wsocks, task.args, launch_cmd_extra_args
            )

        try:
            msg_id = self._invoke_service(self.fwk.component_id, 'init_task_pool', submit_dict)
            allocated_tasks = self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error initiating task pool %s ', task_pool_name)
            raise

        active_tasks = {}
        for task_name in allocated_tasks:
            if launch_interval > 0:
                time.sleep(launch_interval)
            task = queued_tasks[task_name]
            (task_id, command, env_update, cores_allocated) = allocated_tasks[task_name]
            tag = task.keywords.get('tag', 'None')

            active_tasks[task_name] = self._launch_task(
                task.nproc, task.working_dir, task_id, command, cores_allocated, env_update, tag, task.keywords, task.binary, task.args
            )

            if env_update:
                self._send_monitor_event(
                    'IPS_LAUNCH_TASK_POOL',
                    f'task_id = {task_id} , Tag = {tag} , nproc = {task.nproc} , Target = {command} , task_name = {task_name}, env = {env_update}',
                    procs_requested=task.nproc,
                    cores_allocated=cores_allocated,
                )
            else:
                self._send_monitor_event(
                    'IPS_LAUNCH_TASK_POOL',
                    f'task_id = {task_id} , Tag = {tag} , nproc = {task.nproc} , Target = {command} , task_name = {task_name}',
                    procs_requested=task.nproc,
                    cores_allocated=cores_allocated,
                )

        return active_tasks

    def kill_task(self, task_id: int) -> None:
        """Kill launched task *task_id*.  Return if successful.  Raises
        exceptions if the task or process cannot be found or killed
        successfully.

        :param task_id: task ID
        :type task_id: int

        :raises: Exception - if task could not successfully be killed.
        """
        try:
            process = self.task_map[task_id].process
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
            msg_id = self._invoke_service(self.fwk.component_id, 'finish_task', task_id, task_retval)
            self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error finalizing task  %s', task_id)
            raise

    def kill_all_tasks(self) -> None:
        """
        Kill all tasks associated with this component.
        """
        task_id_list = list(self.task_map)
        for task_id in task_id_list:
            try:
                self.kill_task(task_id)
            except Exception:
                raise

    def wait_task_nonblocking(self, task_id: int) -> Union[int, None]:
        """Check the status of task *task_id*.  If it has finished, the
        return value is populated with the actual value, otherwise
        ``None`` is returned.  A *KeyError* exception may be raised if
        the task is not found.

        :param task_id: task ID (PID)
        :type task_id: int

        :return: return value of task if finished else None
        """
        try:
            task = self.task_map[task_id]
            # TODO: process and start_time will have to be accessed as shown
            #      below if this task can be relaunched to support FT...
        except KeyError:
            self.exception('Error: unrecognizable task_id = %s ', task_id)
            raise
        task_retval = task.process.poll()
        if task_retval is None:
            if task.start_time + task.timeout < time.time():
                self.kill_task(task_id)
                self._send_monitor_event('IPS_TASK_END', 'task_id = %s  TIMEOUT elapsed time = %.2f S' % (str(task_id), time.time() - task.start_time))
                return -1
            else:
                return None
        else:
            retval = self.wait_task(task_id)
            return retval

    def wait_task(self, task_id: int, timeout: int = -1, delay: int = 1) -> int:
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
            task = self.task_map[task_id]
        except KeyError:
            self.exception('Error: unrecognizable task_id = %s ', str(task_id))
            raise
        task_retval = None
        if timeout < 0:
            task_retval = task.process.wait()
        else:
            maxtime = task.start_time + timeout
            while time.time() < maxtime:
                task_retval = task.process.poll()
                if task_retval is None:
                    time.sleep(delay)
                else:
                    break

        finish_time = time.time()
        if task_retval is None:
            task.process.kill()
            task_retval = task.process.wait()
            event_comment = 'task_id = %s  TIMEOUT elapsed time = %.2f S' % (str(task_id), finish_time - task.start_time)
        else:
            event_comment = 'task_id = %s  elapsed time = %.2f S' % (str(task_id), finish_time - task.start_time)

        self._send_monitor_event(
            'IPS_TASK_END',
            event_comment,
            start_time=task.start_time,
            end_time=finish_time,
            elapsed_time=finish_time - task.start_time,
            procs_requested=task.nproc,
            cores_allocated=task.cores_allocated,
            target=task.binary,
            operation=' '.join(task.args),
            call_id=task_id,
        )

        del self.task_map[task_id]
        try:
            msg_id = self._invoke_service(self.fwk.component_id, 'finish_task', task_id, task_retval)
            self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error finalizing task  %s', task_id)
            raise
        return task_retval

    def wait_tasklist(self, task_id_list: list[int], block: bool = True) -> dict[int, int]:
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
                process = self.task_map[task_id].process
            except KeyError:
                self.exception('Error: unknown task id : %s', task_id)
                raise
        while len(running_tasks) > 0:
            for task_id in task_id_list:
                if task_id not in running_tasks:
                    continue
                process = self.task_map[task_id].process
                retval = process.poll()
                if retval is not None:
                    task_retval = self.wait_task(task_id)
                    ret_dict[task_id] = task_retval
                    running_tasks.remove(task_id)
            if not block:
                break
            time.sleep(0.05)
        return ret_dict

    def get_config_param(self, param: str, silent: bool = False, log: bool = True) -> Any:
        """
        Return the value of the configuration parameter ``param``.  Raise
        exception if not found and silent is False.

        Config params with special meaning to the framework include:

        - SIM_ROOT (mandatory)
        - SIM_NAME (mandatory)
        - LOG_FILE (mandatory)
        - LOG_LEVEL
        - RUN_ID
        - TOKOMAK_ID
        - SHOT_NUMBER
        - OUTPUT_PREFIX
        - SIMULATION_MODE (either NORMAL or RESTART)
        - NODE_ALLOCATION_MODE (either SHARED or EXCLUSIVE)
        - RESTART_TIME
        - RESTART_ROOT
        - CHECKPOINT
        - TIME_LOOP (this should generally be accessed via `self.services.get_time_loop()`)

        Any variable defined in the config file can be accessed via this function.

        :param param: The parameter requested from simulation config
        :type param: str

        :param silent: If True and parameter isn't found then exception is not raised, default False
        :type silent: bool

        :param log: If silent is False, determine whether or not to record the exception. Set to False if you expect to need to retry this call.
        :type log: bool

        :return: dictionary of given parameter from configuration
        :rtype: dict
        """
        try:
            val = self.sim_conf[param]
        except KeyError:
            try:
                msg_id = self._invoke_service(self.fwk.component_id, 'get_config_parameter', param)
                val = self._get_service_response(msg_id, block=True)
            except Exception:
                if not silent:
                    if log:
                        self.exception('Error retrieving value of config parameter %s', param)
                    raise
                return None
        return val

    def set_config_param(self, param: str, value: Any, target_sim_name: Optional[str] = None) -> Any:
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
        if param in self.sim_conf:
            raise Exception('Cannot dynamically alter simulation configuration parameter ' + param)
        try:
            msg_id = self._invoke_service(self.fwk.component_id, 'set_config_parameter', param, value, sim_name)
            retval = self._get_service_response(msg_id, block=True)
        except Exception:
            self.exception('Error setting value of configuration parameter %s', param)
            raise
        return retval

    def get_time_loop(self) -> list[float]:
        """
        Return the list of times as specified in the configuration file.

        :return: list of times
        :rtype: list of float
        """
        if self.time_loop is not None:
            return self.time_loop
        tlist = []
        time_conf = self.sim_conf['TIME_LOOP']

        def safe(nums):
            return len(set(str(nums)).difference(set('1234567890-+/*.e '))) == 0

        # generate tlist in regular mode (start, finish, step)
        if time_conf['MODE'] == 'REGULAR':
            for entry in ['FINISH', 'START', 'NSTEP']:
                if not safe(time_conf[entry]):
                    self.error('Invalid TIME_LOOP value of %s = %s', entry, time_conf[entry])
                    raise ValueError('Invalid TIME_LOOP value of %s = %s' % (entry, time_conf[entry]))
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

        if mode not in ['ALL', 'WALLTIME_REGULAR', 'WALLTIME_EXPLICIT', 'PHYSTIME_REGULAR', 'PHYSTIME_EXPLICIT']:
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
        self.debug('Checkpointing components after %.3f sec with physics time = %.3f', self.last_ckpt_walltime - self.start_time, self.last_ckpt_phystime)
        self._send_monitor_event('IPS_CHECKPOINT_START', 'Components = ' + str(comp_id_list))
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
            all_chkpts = [os.path.basename(f) for f in glob.glob(os.path.join(base_dir, '*')) if os.path.isdir(f)]
            prior_runs_chkpts_dirs = [chkpt for chkpt in all_chkpts if chkpt not in self.new_chkpts]
            purge_candidates = sorted(prior_runs_chkpts_dirs, key=float)
            purge_candidates += [chkpt for chkpt in self.new_chkpts if (chkpt in all_chkpts and chkpt not in self.protected_chkpts)]
            while len(purge_candidates) > num_chkpt:
                obsolete_chkpt = purge_candidates.pop(0)
                chkpt_dir = os.path.join(base_dir, obsolete_chkpt)
                try:
                    shutil.rmtree(chkpt_dir)
                except Exception:
                    self.exception('Error removing directory %s', chkpt_dir)
                    raise
        self._send_monitor_event('IPS_CHECKPOINT_END', 'Components = ' + str(comp_id_list))
        return ret_dict

    # DM getWorkDir
    def get_working_dir(self) -> str:
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
            self.workdir = os.path.join(self.sim_conf['SIM_ROOT'], 'work', self.full_comp_id)
        return self.workdir

    # DM stageInput
    def stage_input_files(self, input_file_list: Union[str, Iterable[str]]) -> None:
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

        targetdir = os.path.join(simroot, 'simulation_setup', self.full_comp_id)
        try:
            ipsutil.copyFiles(inputDir, input_file_list, targetdir, outprefix)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_INPUTS', 'Files = ' + str(input_file_list) + ' Exception raised : ' + str(e), ok=False)
            self.exception('Error in stage_input_files')
            raise e
        for _, old_conf, _, _ in self.sub_flows.values():
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
                    self._send_monitor_event('IPS_STAGE_INPUTS', 'Files = ' + str(input_files) + ' Exception raised : ' + str(e), ok=False)
                    self.exception('Error in stage_input_files')
                    raise e
        elapsed_time = time.time() - start_time
        self._send_monitor_event(
            eventType='IPS_STAGE_INPUTS',
            comment='Elapsed time = %.3f Path = %s Files = %s' % (elapsed_time, os.path.abspath(inputDir), str(input_file_list)),
            start_time=start_time,
            elapsed_time=elapsed_time,
            target='stage_input_files',
            operation=str(input_file_list),
        )

    def stage_subflow_output_files(self, subflow_name: str = 'ALL') -> dict[str, list[str]]:
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
                self.exception('Subflow name %s not found' % subflow_name)
                raise Exception('Subflow name %s not found' % subflow_name) from None

        return_dict = {}
        for sim_name, (sub_conf_new, _, _, driver_comp) in subflow_dict.items():
            driver = sub_conf_new[sub_conf_new['PORTS']['DRIVER']['IMPLEMENTATION']]
            output_dir = os.path.join(
                sub_conf_new['SIM_ROOT'], 'work', '_'.join([driver['CLASS'], driver['SUB_CLASS'], driver['NAME'], str(driver_comp.get_seq_num())])
            )
            output_files = driver['OUTPUT_FILES']
            try:
                ipsutil.copyFiles(output_dir, output_files, self.get_working_dir(), keep_old=False)
            except Exception as e:
                self._send_monitor_event('IPS_STAGE_SUBFLOW_OUTPUTS', 'Files = ' + str(output_files) + ' Exception raised : ' + str(e), ok=False)
                self.exception('Error in stage_subflow_output_files() for subflow %s' % sim_name)
                raise
            else:
                if isinstance(output_files, str):
                    return_dict[sim_name] = output_files.split()
                else:
                    return_dict[sim_name] = output_files
        return return_dict

    def stage_output_files(self, timeStamp: float, file_list: Union[str, list[str]], keep_old_files: bool = True, save_plasma_state: bool = True) -> None:
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

        output_dir = os.path.join(sim_root, out_root, str(timeStamp), 'components', self.full_comp_id)
        if isinstance(file_list, str):
            file_list = file_list.split()
        all_files = functools.reduce(iadd, [glob.glob(f) for f in file_list], [])
        try:
            ipsutil.copyFiles(workdir, all_files, output_dir, outprefix, keep_old=keep_old_files)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_OUTPUTS', 'Files = ' + str(file_list) + ' Exception raised : ' + str(e), ok=False)
            self.exception('Error in stage_output_files()')
            raise

        # Store plasma state files into $SIM_ROOT/history/plasma_state
        # Plasma state files are renamed, by appending the full component
        # name (CLASS_SUBCLASS_NAME) and timestamp to the file name.
        # A version number is added to the end of the file name to avoid
        # overwriting existing plasma state files
        plasma_dir = os.path.join(self.sim_conf['SIM_ROOT'], 'simulation_results', 'plasma_state')
        try:
            os.makedirs(plasma_dir, exist_ok=True)
        except OSError as e:
            self._send_monitor_event('IPS_STAGE_OUTPUTS', 'Files = ' + str(file_list) + ' Exception raised : ' + e.strerror, ok=False)
            self.exception('Error creating directory %s : %d-%s', plasma_dir, e.errno, e.strerror)
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
                newName = '_'.join([outprefix + name, self.full_comp_id, str(timeStamp)]) + '.' + ext
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
                self.exception('Error copying file: %s from %s to %s - %s', f, workdir, target_name, str(why))
                self._send_monitor_event('IPS_STAGE_OUTPUTS', 'Files = ' + str(file_list) + ' Exception raised : ' + str(why), ok=False)
                raise

        # Store symlinks to component output files in a single top-level directory

        symlink_dir = os.path.join(sim_root, out_root, self.full_comp_id)
        try:
            os.makedirs(symlink_dir, exist_ok=True)
        except OSError as e:
            self.exception('Error creating directory %s : %s', symlink_dir, e.strerror)
            raise

        all_files = functools.reduce(iadd, [glob.glob(f) for f in file_list], [])

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
            file_suffix = real_file.split('/')[len(common) :]  # Include file name
            link_suffix = sym_link.split('/')[len(common) : -1]  # No file name
            p = []
            if len(link_suffix) > 0:
                p = ['../' * len(link_suffix)]
            p = p + file_suffix
            relpath = os.path.join(*p)
            os.symlink(relpath, sym_link)

        elapsed_time = time.time() - start_time
        self._send_monitor_event(
            'IPS_STAGE_OUTPUTS',
            'Elapsed time = %.3f Path = %s Files = %s' % (elapsed_time, output_dir, str(file_list)),
            start_time=start_time,
            elapsed_time=elapsed_time,
            target='stage_output_files',
            operation=str(file_list),
        )

    def save_restart_files(self, timeStamp: float, file_list: Union[str, list[str]]) -> None:
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

        targetdir = os.path.join(base_dir, timeStamp_str, '_'.join([conf['CLASS'], conf['SUB_CLASS'], conf['NAME']]))
        self.debug('Checkpointing: Copying %s to dir %s', str(file_list), targetdir)

        try:
            ipsutil.copyFiles(workdir, file_list, targetdir)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_RESTART', 'Files = ' + str(file_list) + ' Exception raised : ' + str(e), ok=False)
            self.exception('Error in stage_restart_files()')
            raise

        self._send_monitor_event('IPS_SAVE_RESTART', 'Files = ' + str(file_list))

    def get_restart_files(self, restart_root: str, timeStamp: float, file_list: Union[str, list[str]]) -> None:
        """
        Copy files needed for component restart from the restart directory::

            <restart_root>/restart/<timeStamp>/components/$CLASS_${SUB_CLASS}_$NAME_${SEQ_NUM}

        to the component's work directory.

        Copying errors are not fatal (exception raised).
        """
        work_dir = self.get_working_dir()

        conf = self.component_ref.config
        base_dir = os.path.join(restart_root, 'restart', '%.3f' % (float(timeStamp)))
        source_dir = os.path.join(base_dir, '_'.join([conf['CLASS'], conf['SUB_CLASS'], conf['NAME']]))

        try:
            ipsutil.copyFiles(source_dir, file_list, work_dir)
        except Exception as e:
            self._send_monitor_event('IPS_GET_RESTART', 'Files = ' + str(file_list) + ' Exception raised : ' + str(e), ok=False)
            self.exception('Error in get_restart_files()')
            raise

        self._send_monitor_event('IPS_GET_RESTART', 'Files = ' + str(file_list))

    def stage_state(self, state_files: Optional[list[str]] = None) -> None:
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
            msg_id = self._invoke_service(self.fwk.component_id, 'stage_state', files, state_dir, workdir)
            self._get_service_response(msg_id, block=True)
        except Exception as e:
            self._send_monitor_event('IPS_STAGE_STATE', ' Exception raised : ' + str(e), ok=False)
            self.exception('Error staging state files')
            raise
        elapsed_time = time.time() - start_time
        self._send_monitor_event(
            'IPS_STAGE_STATE',
            'Elapsed time = %.3f  files = %s Success' % (elapsed_time, ' '.join(files)),
            start_time=start_time,
            elapsed_time=elapsed_time,
            target='stage_state',
            operation=str(files),
        )

    def update_state(self, state_files: Optional[list[str]] = None) -> None:
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
            msg_id = self._invoke_service(self.fwk.component_id, 'update_state', files, workdir, state_dir)
            self._get_service_response(msg_id, block=True)
        except Exception as e:
            print('Error updating state files', str(e), file=sys.stderr)
            self._send_monitor_event('IPS_UPDATE_STATE', ' Exception raised : ' + str(e), ok=False)
            self.exception('Error updating state files')
            raise
        elapsed_time = time.time() - start_time
        self._send_monitor_event(
            'IPS_UPDATE_STATE',
            'Elapsed time = %.3f   files = %s Success' % (elapsed_time, ' '.join(files)),
            start_time=start_time,
            elapsed_time=elapsed_time,
            target='update_state',
            operation=str(files),
        )

    def merge_current_state(self, partial_state_file: str, logfile: Optional[str] = None, merge_binary: Optional[str] = None) -> None:
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
        bin_name = merge_binary if merge_binary else 'update_state'
        full_path_binary = ipsutil.which(bin_name)
        if not full_path_binary:
            self.error('Missing executable %s in PATH', bin_name)
            raise FileNotFoundError('Missing executable file %s in PATH' % bin_name)
        try:
            msg_id = self._invoke_service(self.fwk.component_id, 'merge_current_plasma_state', update_file, source_plasma_file, logfile, full_path_binary)
            ret_val = self._get_service_response(msg_id, block=True)
        except Exception as e:
            print('Error merging state files', str(e), file=sys.stderr)
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE', ' Exception raised : ' + str(e), ok=False)
            self.exception('Error merging plasma state file ' + partial_state_file)
            raise
        if ret_val == 0:
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE', 'Success')
            return
        else:
            self._send_monitor_event('IPS_MERGE_PLASMA_STATE', ' Error in call to update_state() : ', ok=False)
            self.error('Error merging update %s into current plasma state file %s', partial_state_file, current_plasma_state)
            raise Exception('Error merging update %s into current plasma state file %s' % (partial_state_file, current_plasma_state))

    def update_time_stamp(self, new_time_stamp=-1) -> None:
        """
        Update time stamp on portal.
        """
        event_data = {}
        event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
        event_data['real_sim_name'] = self.sim_name

        portal_data = {}
        portal_data['phystimestamp'] = new_time_stamp
        portal_data['eventtype'] = 'PORTALBRIDGE_UPDATE_TIMESTAMP'
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTALBRIDGE_UPDATE_TIMESTAMP', event_data)
        self._send_monitor_event('IPS_UPDATE_TIME_STAMP', 'Timestamp = ' + str(new_time_stamp))

    def setMonitorURL(self, url: str = '') -> None:
        """
        Send event to portal setting the URL where the monitor component will
        put data.
        """
        self.monitor_url = url
        self._send_monitor_event(eventType='IPS_SET_MONITOR_URL', comment='SUCCESS')

    def _should_use_portal(self) -> bool:
        """Return True if we want to use the portal, False if not"""
        use_portal_config = self.get_config_param('USE_PORTAL', silent=True)

        if isinstance(use_portal_config, str):
             return use_portal_config.strip().lower() == 'true'
        elif use_portal_config is None:
            return False
        else:
            # Because USE_PORTAL was not set in config file, or was mistakenly set as a dictionary.
            self.warning('Unusual value for USE_PORTAL: %s', use_portal_config)
            return False

    def _establish_portal_runid(self) -> None:
        """Get the runid Jupyter and the Portal will associate with this run.
        Generally this will be the runid that the portal emits, but we will try to allow for fallbacks in certain cases.

        If value >= 0, we have the portal runid
        If value == -1, we have not yet set the portal runid
        If value == -2, we have tried and failed to get the portal runid, and will not try again

        You should explicitly check the value of self._portal_runid after this function, as this function is concerned with setting the value in a thread-safe context.
        """

        # first, check if portal_runid was already set
        if self._portal_runid_event.is_set():
            return

        # first, check to see if we even want to use the portal
        if not self._should_use_portal():
            self.warning('web portal disabled')
            self._portal_runid = -2
            self._portal_runid_event.set()
            return

        # next, check to see if the portal URL was even initialized, fall back if not
        if not self.get_config_param('PORTAL_URL', silent=True):
            self.warning('_get_jupyter_runid: PORTAL_URL was not defined, disabling Jupyter workflow')
            self._portal_runid = -2
            self._portal_runid_event.set()
            return
        
        # next, check to see if the user remembered to define an API key (adding data requires a runid)
        if not self.get_config_param('_IPS_PORTAL_API_KEY', silent=True):
            self.warning('_get_jupyter_runid: PORTAL_API_KEY was not defined, disabling Jupyter workflow')
            self._portal_runid = -2
            self._portal_runid_event.set()
            return

        # Here, we will periodically check to see if we have our config param set
        # The IPS Portal Bridge component will set this after it gets a response back from the IPS_START event
        # Inside this IPS_START event is the runid as maintained by the IPS Portal itself

        attempts = 0
        max_attempts = 10
        base_time = time.time()

        # if the event flag is set from another call, self._portal_runid should also be set to a non-default value, so break early
        while not self._portal_runid_event.is_set():
            try:
                # We expect to fail this call a few times, so do not log the failed attempts
                value = self.get_config_param('_IPS_PORTAL_RUNID', log=False)
                try:
                    value = int(value)
                except Exception:
                    self.warning('got back invalid value for runid from portal: %s', value)
                    self._portal_runid = -2
                    self._portal_runid_event.set()
                    return
                self._portal_runid = value
                self._portal_runid_event.set()
                self.info('took this long to obtain PORTAL_RUNID: %d', time.time() - base_time)
                return
            except Exception:
                attempts += 1
                if attempts >= max_attempts:
                    self.warning('_get_jupyter_runid: Unable to get RUNID directly from remote portal, disabling Jupyter workflow')
                    self._portal_runid = -2
                    self._portal_runid_event.set()
                    self.warning('took this amount of time to reach max attempts: %d', time.time() - base_time)
                    return
                self._portal_runid_event.wait(1.0)

    def initialize_jupyter_notebook(
        self,
        source_notebook_path: str,
        dest_notebook_name: Optional[str] = None,
    ) -> None:
        """If the IPS Portal is available, this function loads a notebook from source_notebook_path, adds a cell to load the data, and then saves the concatenated notebook to the Portal.

        If a connection to the IPS Portal cannot be verified for this run, this function does nothing.

        Does not modify the source notebook.

        :param source_notebook_path: location you want to load the source notebook from. This can be either an absolute path, or an IPS-appropriate relative path.
        :param dest_notebook_name: (optional, default None) filename of the notebook to use when saving it to the IPS Portal. If not provided, this will defauly to the filename of the source notebook.
        """
        # have we initialized a runid yet? if not, block this function call until we can establish or not establish one
        if not self._portal_runid_event.is_set():
            self._establish_portal_runid()
        
        # now check to see if we have a valid runid
        if self._portal_runid < 0:
            return

        if not os.path.exists(source_notebook_path):
            msg = f'Path to notebook {source_notebook_path} does not exist'
            self.error(msg)
            raise FileNotFoundError(msg)

        if dest_notebook_name is None:
            dest_notebook_name = os.path.basename(source_notebook_path)
        else:
            dest_notebook_name = os.path.basename(dest_notebook_name)

        event_data = {}
        event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
        event_data['real_sim_name'] = self.sim_name

        portal_data: dict[str, Any] = {}
        portal_data['eventtype'] = 'PORTAL_REGISTER_NOTEBOOK'
        portal_data['data_source'] = os.path.join(os.getcwd(), source_notebook_path) if not os.path.isabs(source_notebook_path) else source_notebook_path
        portal_data['username'] = self.get_config_param('USER')
        portal_data['filename'] = dest_notebook_name
        portal_data['portal_runid'] = self._portal_runid
        event_data['portal_data'] = portal_data
        self.publish('_IPS_MONITOR', 'PORTAL_REGISTER_NOTEBOOK', event_data)
        self._send_monitor_event('IPS_PORTAL_REGISTER_NOTEBOOK', f'FILENAME = {dest_notebook_name}')

    def add_analysis_data_files(self, current_data_file_paths: list[str], timestamp: float = 0.0, replace: bool = False) -> None:
        """If the IPS Portal is available, saves data files to IPS Portal. Files are indexed via specific timestamps.

        If a connection to the IPS Portal cannot be verified for this run, this function does nothing.

        :param current_data_file_paths: list of paths to the current data files we want to copy to the Jupyter directory. These paths may be either absolute paths or IPS-appropriate relative paths. If path is a directory, add all files in directory and preserve directory structure on the IPS Portal.
        :param timestamp: label to assign to the data (currently must be a floating point value)
        :param replace: If True, replace the last data file added with the new data file. If False, simply append the new data file. (default: False)
              Note that if replace is not True but you attempt to overwrite it, a ValueError will be thrown.
        """
        # have we initialized a runid yet? if not, block this function call until we can establish or not establish one
        if not self._portal_runid_event.is_set():
            self._establish_portal_runid()

        # now check to see if we have a valid runid
        if self._portal_runid < 0:
            return

        for source in current_data_file_paths:
            if not os.path.exists(source):
                self.warning(f'file {source} does not exist, skipping it')
                continue
            filename = os.path.basename(source)

            event_data = {}
            event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
            event_data['real_sim_name'] = self.sim_name

            portal_data: dict[str, Any] = {}
            portal_data['eventtype'] = 'PORTAL_ADD_JUPYTER_DATA'
            portal_data['data_source'] = os.path.join(os.getcwd(), source) if not os.path.isabs(source) else source
            portal_data['username'] = self.get_config_param('USER')
            portal_data['filename'] = filename
            portal_data['tag'] = timestamp
            portal_data['replace'] = replace
            portal_data['portal_runid'] = self._portal_runid
            event_data['portal_data'] = portal_data
            self.publish('_IPS_MONITOR', 'PORTAL_ADD_JUPYTER_DATA', event_data)
            self._send_monitor_event('IPS_PORTAL_ADD_JUPYTER_DATA', f'SOURCE = {source} TIMESTAMP = {timestamp} REPLACE = {replace}')

    def publish(self, topicName: str, eventName: str, eventBody: Any) -> None:
        """
        Publish event consisting of *eventName* and *eventBody* to topic *topicName* to the IPS event service.

        Publishing an event multiple components are subscribed to will cause each component to handle the message simultaneously.

        :param topicName: the name of the topic to publish on, top-level namespace
        :param eventName: event associated with the topic 
        :param eventBody: data to send
        """
        if not topicName.startswith('_IPS'):
            topicName = self.sim_name + '_' + topicName
        self.event_service.publish(topicName, eventName, eventBody)

    def subscribe(self, topicName: str, callback: Callable) -> None:
        """
        Subscribe to topic *topicName* on the IPS event service and register *callback* as the method to be invoked when an event is published to that topic.

        Multiple components can subscribe to the same topic name; if this is the case, each component will handle the message separately when the topic is published to.
        
        :param topicName: the name of the topic to subscribe to, top-level namespace
        :param callback: the function which will be called on receiving a message
        """
        if not topicName.startswith('_IPS'):
            topicName = self.sim_name + '_' + topicName
        self.event_service.subscribe(topicName, callback)

    def unsubscribe(self, topicName: str) -> None:
        """
        Remove subscription to topic *topicName*.

        :param topicName: the name of the topic to unsubscribe from
        """
        if not topicName.startswith('_IPS'):
            topicName = self.sim_name + '_' + topicName
        self.event_service.unsubscribe(topicName)

    def process_events(self) -> None:
        """
        Poll for events on subscribed topics.
        """
        self.event_service.process_events()

    def send_portal_event(self, event_type: str = 'COMPONENT_EVENT', event_comment: str = '', event_time=None, elapsed_time=None):
        """
        Send event to web portal.
        """
        return self._send_monitor_event(eventType=event_type, comment=event_comment, event_time=event_time, elapsed_time=elapsed_time)

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

    def info(self, msg: object, *args):
        """
        Produce **informational** message in simulation log file. See :func:`logging.info` for usage.
        """
        self.logger.info(msg, *args)

    def warning(self, msg: object, *args):
        """
        Produce **warning** message in simulation log file. See :func:`logging.warning` for usage.
        """
        self.logger.warning(msg, *args)

    def error(self, msg: object, *args):
        """
        Produce **error** message in simulation log file. See :func:`logging.error` for usage.
        """
        self.logger.error(msg, *args)

    def exception(self, msg: object, *args):
        """
        Produce **exception** message in simulation log file. See :func:`logging.exception` for usage.
        """
        self.logger.exception(msg, *args)

    def critical(self, msg: object, *args):
        """
        Produce **critical** message in simulation log file. See :func:`logging.critical` for usage.
        """
        self.logger.critical(msg, *args)

    def create_task_pool(self, task_pool_name: str):
        """
        Create an empty pool of tasks with the name *task_pool_name*.  Raise exception if duplicate name.
        """
        if task_pool_name in self.task_pools:
            raise Exception('Error: Duplicate task pool name %s' % (task_pool_name))
        self.task_pools[task_pool_name] = TaskPool(task_pool_name, self)

    def add_task(self, task_pool_name: str, task_name: str, nproc: int, working_dir: str, binary: str, *args, **keywords):
        """
        Add task *task_name* to task pool *task_pool_name*.  Remaining arguments are the same as
        in :py:meth:`ServicesProxy.launch_task`.
        """
        task_pool = self.task_pools[task_pool_name]
        # Yep.  Explicitly setting `keywords` to the `keywords` argument.
        # Because if you don't then this will fail because it expects that.
        # FIXME This is an abomination.  Why not just pass `keywords`?
        # And an undocumented side-effect.
        return task_pool.add_task(task_name, nproc, working_dir, binary, *args, keywords=keywords)

    def submit_tasks(
        self,
        task_pool_name,
        block=True,
        use_dask=False,
        dask_nodes=1,
        dask_ppw=None,
        launch_interval=0.0,
        use_shifter=False,
        shifter_args=None,
        dask_worker_plugin=None,
        dask_worker_per_gpu=False,
        oversubscribe=False,
        hwthreads=False,
    ):
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
        retval = task_pool.submit_tasks(
            block, use_dask, dask_nodes, dask_ppw, launch_interval, use_shifter, shifter_args, dask_worker_plugin, dask_worker_per_gpu, oversubscribe, hwthreads
        )
        elapsed_time = time.time() - start_time
        self._send_monitor_event('IPS_TASK_POOL_END', 'task_pool = %s  elapsed time = %.2f S' % (task_pool_name, elapsed_time), elapsed_time=elapsed_time)
        return retval

    def get_finished_tasks(self, task_pool_name: str):
        """
        Return dictionary of finished tasks and return values in task pool *task_pool_name*.  Raise exception if no active or finished tasks.
        """
        task_pool = self.task_pools[task_pool_name]
        return task_pool.get_finished_tasks_status()

    def remove_task_pool(self, task_pool_name: str):
        """
        Kill all running tasks, clean up all finished tasks, and delete task pool.
        """
        task_pool = self.task_pools[task_pool_name]
        task_pool.terminate_tasks()
        del self.task_pools[task_pool_name]

    def create_sub_workflow(self, sub_name, config_file, override: Optional[dict[str, Any]] = None, input_dir=None):
        """Create sub-workflow

        :param sub_name: name of sub-workflow
        :param config_file: configuration file for sub-workflow
        :param override: dictionary of configuration overrides; keys are component names
            and the items are attribute/key values associated with that
            component.
        :param input_dir: input directory for sub-workflow components
        :returns: tuple of simulation name, init component, driver component
        """
        # TODO Unclear on what override is
        if override is None:
            override = {}

        # So subflows have names and they must be unique.
        # TODO how is self.sub_flows set?
        if sub_name in self.sub_flows:
            self.error('Duplicate sub flow name')
            raise Exception('Duplicate sub flow name')

        # TODO We keep track of the number of subflows.  Why?  Also, this is
        # not used anywhere.  Moreover, there is no mechanism for decrementing
        # this count when a subflow finishes.
        self.subflow_count += 1

        # TODO We create *two* ConfigObjs from the *same* config file.  Presumably
        # to do a delta between the two? Why do this?  Also, clone the first
        # instead of reading it again.
        try:
            sub_conf_new = ConfigObj(infile=config_file, interpolation='template', file_error=True)
            sub_conf_old = ConfigObj(infile=config_file, interpolation='template', file_error=True)
        except Exception:
            self.exception('Error accessing sub-workflow config file %s', config_file)
            raise

        # Update undefined sub workflow configuration entries using top level configuration
        # only applicable to non-component entries (ones with non-dictionary values)
        for k, v in self.sim_conf.items():
            if k not in sub_conf_new and not isinstance(v, dict):
                sub_conf_new[k] = v

        # TODO Where is self.sim_name set?  What is the significance of
        # SIM_NAME and SIM_ROOT?
        sub_conf_new['SIM_NAME'] = self.sim_name + '::' + sub_name
        sub_conf_new['SIM_ROOT'] = os.path.join(os.getcwd(), sub_name)
        # sub_conf_new['SIM_ROOT'] = os.path.join(os.getcwd(), 'sub_workflow_%d' % self.subflow_count)
        # Update INPUT_DIR for components to current working dir (super simulation working dir)
        ports = sub_conf_new['PORTS']['NAMES'].split()

        # This is the set of components in the subflow as dictated in the
        # PORTS section.  Each subsection will have an IMPLEMENTATION value
        # that refers to a component in the subflow.
        components = [sub_conf_new['PORTS'][p]['IMPLEMENTATION'] for p in ports]

        # Associate the corresponding INPUT_DIR, which is the working directory
        # for the given port. If the user specified an `input_dir` in this call,
        # then prefer to use that, otherwise use any INPUT_DIR specified by
        # the port in the configuration file.
        for c in components:
            if not c:
                continue
            if input_dir is None:
                sub_conf_new[c]['INPUT_DIR'] = os.path.join(os.getcwd(), c)
            else:
                sub_conf_new[c]['INPUT_DIR'] = os.path.join(os.getcwd(), input_dir)

            # Handle any overrides for the component
            try:  # FIXME this cold be refactored to not use try/except
                override_vals = override[c]
            except KeyError:
                pass
            else:
                for k, v in override_vals.items():
                    sub_conf_new[c][k] = v

        # Handle any overrides for the top level configuration
        toplevel_override = set(override.keys()) - set(components)
        for param in toplevel_override:
            sub_conf_new[param] = override[param]

        # TODO Why do you overwrite the config file?
        sub_conf_new.filename = os.path.basename(config_file)
        sub_conf_new.write()
        try:  # FIXME, if you're going to catch an exception, you should handle it
            (sim_name, init_comp, driver_comp) = self._create_simulation(os.path.abspath(sub_conf_new.filename), {}, sub_workflow=True)
        except Exception:
            raise

        self.sub_flows[sub_name] = (sub_conf_new, sub_conf_old, init_comp, driver_comp)
        self._send_monitor_event('IPS_CREATE_SUB_WORKFLOW', 'workflow_name = %s' % sub_name)
        return (sim_name, init_comp, driver_comp)

    def create_simulation(self, config_file, override):
        """Create simulation"""
        return self._create_simulation(config_file, override, sub_workflow=False)[0]

    def _create_simulation(self, config_file, override, sub_workflow=False):
        """
        :param config_file: configuration file for simulation
        :param override: dict of configuration file overrides
        :param sub_workflow: boolean indicating if this is a sub-workflow
        :returns: tuple of simulation name, init component, driver component
        """
        try:
            msg_id = self._invoke_service(self.fwk.component_id, 'create_simulation', config_file, override, sub_workflow)
            self.debug('create_simulation() msg_id = %s', msg_id)
            (sim_name, init_comp, driver_comp) = self._get_service_response(msg_id, block=True)
            self.debug('Created simulation %s', sim_name)
        except Exception:
            self.exception('Error creating new simulation')
            raise
        return (sim_name, init_comp, driver_comp)

    def run_ensemble(
        self,
        template: Union[str, os.PathLike],
        variables: dict[str, dict[str, list[str]]],
        run_dir: Union[str, os.PathLike],
        name: str,
        num_nodes: int,
        cores_per_instance: Optional[int] = None,
        oversubscribe: bool = False,
        hwthreads: bool = False,
    ):
        """Run ensemble of simulations given the template and variables.

        `variables` is a nested dict that looks like this:

        .. code-block:: python

                variables = {'a_sim_comp': {'A': [3, 2, 4],
                                            'B': [2.34, 5.82, 0.1],
                                            'C': ['bar', 'baz', 'quux']},
                            'another_sim_comp': {'D': [7, 5, 9],
                                                 'B': [0.775, 0.080, 29.2],
                                                 'F': ['xyzzy', 'plud', 'thud']}}

        That is, the keys are the simulation names and the values are dicts
        mapping parameter to a set of values.  Ensembles will be spun
        up for each simulation for each combination of parameters.  E.g.,
        `a_sim_comp` will be run three times with the parameters of A, B, and C
        being set to 3, 2.34, 'bar' for one of the simulation instances,
        respectively.  another_sim_comp behaves similarly with its
        respective parameters.

        The ensembles will run under `run_dir` within a subdirectory
        uniquely named for each.  The subdirectory will contain an IPS
        config file created from `template` with `?` variables replaced
        with the values from `variables`.

        TODO be able to specify the number of cores per instance

        :param template: configuration template file
        :param variables: a dict of variables to pass to the ensemble runs
        :param run_dir: in which to run the ensembles
        :param name: ensemble name, or string to prepend to generated instance
            directory and file names
        :param cores_per_instance: How many cores per ensemble instances?
        :param num_nodes: Total number of nodes to allocate for the ensemble
            runs. There will be one Dask worker assigned to each of these
            nodes.
        :param oversubscribe: Whether to allow oversubscription of nodes
            when launching the ensemble runs. Default is False.
        :param hwthreads: Whether to use hardware threads
        :returns: a list of dicts mapping created subdirs to simulation names
            and their parameters
        """
        # This should be a unique variable across all ensembles we keep track
        # of in the portal This ID should only be shared by runs within an
        # ensemble
        portal_ensemble_id = str(uuid.uuid4())

        use_portal = self._should_use_portal()

        self.debug(f'use portal = {use_portal!s}')

        def create_driver_config_file(template,
                                      working_dir,
                                      variables,
                                      name,
                                      use_portal):
            """Create an IPS config file for an ensemble instance

            :param template: ConfigObj from which to derive the config file
            :param working_dir: in which to put the config file
            :param variables: component parameters that need to be plugged
                into the template
            :param name: instance string prefix for file names
            :param use_portal: whether to use portal
            :returns: The file name of the created driver config file
            """
            # ensure working_dir is Path obj since we use / operators later; no
            # harm if it's already a Path obj.
            working_dir = Path(working_dir)

            # As a convenience, assign the ensemble instance name to
            # ENSEMBLE_INSTANCE so that the user can optionally use that string
            # in their reporting.
            template['ENSEMBLE_INSTANCE'] = name
            template['_IPS_PORTAL_ENSEMBLE_ID'] = portal_ensemble_id
            template['SIM_NAME'] = name

            if 'SIM_ROOT' in template and \
                    template['SIM_ROOT'] is not None and \
                    template['SIM_ROOT'].strip() != '':
                self.info(f'SIM_ROOT in template config assigned a value, '
                          f'{template["SIM_ROOT"]}, that will be ignored')

            # Ensure that the instance gets a unique directory for its work
            # by setting SIM_ROOT to the prefix path.
            template['SIM_ROOT'] = Path(working_dir)

            # Handle portal configuration, note that PORTAL_API_KEY should be
            # an environment variable and will be passed in later.
            self.debug(f'use_portal inside create_driver_config_file: '
                       f'{use_portal}, with type {type(use_portal)}')
            if use_portal:
                self.debug(f'USE_PORTAL is True, so emitting PORTAL variables.')
                # WARNING: portal_runid is set asynchronously by the Portal
                # Bridge, wait for it to be set currently, the value we use
                # in the config file is the value the Bridge component itself
                # generates eventually, would like to rework this so we avoid
                # ever setting this UUID value (and sending it to the
                # portal), only using and sending the actual portal-generated
                # value
                portal_runid = None
                while portal_runid is None:
                    self.debug('Attempting to get portal run ID')
                    portal_runid = self.get_config_param('PORTAL_RUNID',
                                                         silent=True)
                self.debug(f'Using portal run ID: {portal_runid}')

                portal_url = self.get_config_param('PORTAL_URL',
                                                   silent=True)

                template['PORTAL_URL'] = portal_url
                template['USE_PORTAL'] = 'True'
                template['PARENT_PORTAL_RUNID'] = portal_runid
            else:
                self.debug('USE_PORTAL is False, so propagating that to '
                           'ensemble instance config file.')
                template['USE_PORTAL'] = 'False'

            # We need to plug in the variables, so we need to find the section
            # for a each component, and then find the corresponding variables
            # to then assign the associated value.
            for component in variables:
                self.debug(f'Substituting for {component[0]}')

                for variable in component[1].keys():
                    # Substitute the individual variables for this component
                    self.debug(f'Assigning {component[1][variable]} to {variable}')
                    template[component[0]][variable] = component[1][variable]

            template['LOG_FILE'] = working_dir / Path(name + '_run.log')
            template_filename = working_dir / Path(name + '.config')
            template.filename = template_filename
            template.write()

            return template_filename

        def create_platform_config_file(prefix, working_dir, cores_per_instance, **kwargs):
            """
            Create a platform config file for the ensemble instance.

            TODO consider moving to platformspec.py since this is platform
                specific.

            :param prefix: instance string prefix for file names
            :param working_dir: in which to put the platform config file
            :param kwargs: optional platform specific parameters
            :returns: platform config file name
            """
            platform_config_file_path = Path(working_dir) / Path(prefix + '_platform.config')
            self.debug(f'Creating platform config file {platform_config_file_path}')

            platform_config = ConfigObj()
            platform_config.filename = str(platform_config_file_path)

            # Though in a batch submission context this may not have much
            # meaning.
            platform_config['HOST'] = socket.gethostname()

            # Regardless, faithfully duplicate the MPIRUN setting from the
            # top-level platform config, which is what the user has set. Same
            # with node detection.
            platform_config['MPIRUN'] = 'mpirun'
            platform_config['NODE_DETECTION'] = 'manual'

            # This is critical for ensuring that `prun` is used to run the
            # ensemble instances.  This is because the ensemble instances rely
            # on the DVM (Dynamic Virtual Machine) to run the simulations,
            # which was spun up in the docker worker plugin, `DVMPlugin`. The
            # `prun` *should* use the environment variables set by the plugin
            # to find the DVM.
            platform_config['MPIRUN_VERSION'] = 'OPENMPI-DVM'

            # Set the budget of cores per instance. By default, we will give
            # a single core per instance.
            if cores_per_instance is not None:
                platform_config['CORES_PER_NODE'] = cores_per_instance
                platform_config['PROCS_PER_NODE'] = cores_per_instance
            else:
                platform_config['CORES_PER_NODE'] = 1
                platform_config['PROCS_PER_NODE'] = 1

            # for now each instance will always run on just one node
            platform_config['NODES'] = 1

            # TODO going to ignore this for now; consider that the user
            # specifying TOTAL_PROCS at the top-level platform config doesn't
            # apply to the _instances_ that should only "see" the number of
            # actual cores allocated via prun.
            # # inherit total processors from top-level platform config
            # total_procs = self.get_config_param('TOTAL_PROCS', silent=True)
            # if total_procs is not None and total_procs > 0:
            #     # Propagate the total processors to the platform config if
            #     # it is defined and greater than zero.  Note that at the top-
            #     # level it will default to zero if not defined, so we also
            #     # check for that; i.e., if non-zero, we propagate that to
            #     # each instance platform config file.
            #     platform_config['TOTAL_PROCS'] = total_procs

            # Set the number of sockets per node; this is a platform specific
            # Kept for backward compatibility; FIXME this should be deprecated
            platform_config['SOCKETS_PER_NODE'] = 1

            # define node allocation mode to be shared since we'll have more
            # than one ensemble instance per node.
            platform_config['NODE_ALLOCATION_MODE'] = 'SHARED'

            platform_config.write()

            return platform_config_file_path

        def send_ensemble_instance_to_portal(ensemble_name: str, data_path: Path) -> None:
            # Make sure we actually want to use the portal in the first place
            if not use_portal:
                return

            # have we initialized a runid yet? if not, block this function call until we can establish or not establish one
            if not self._portal_runid_event.is_set():
                self._establish_portal_runid()
            
            # now check to see if we have a valid runid
            if self._portal_runid < 0:
                return
            event_data = {}
            event_data['sim_name'] = self.sim_conf['__PORTAL_SIM_NAME']
            event_data['real_sim_name'] = self.sim_name

            portal_data: dict[str, Any] = {}
            portal_data['eventtype'] = 'PORTAL_UPLOAD_ENSEMBLE_PARAMS'
            portal_data['component_name'] = self.component_ref.config['NAME']
            portal_data['ensemble_name'] = ensemble_name
            portal_data['ensemble_id'] = portal_ensemble_id
            portal_data['ensemble_data_path'] = data_path
            portal_data['username'] = self.get_config_param('USER')
            portal_data['portal_runid'] = self._portal_runid
            event_data['portal_data'] = portal_data
            self.publish('_IPS_MONITOR', 'PORTAL_UPLOAD_ENSEMBLE_PARAMS', event_data)
            self._send_monitor_event('IPS_PORTAL_UPLOAD_ENSEMBLE_PARAMS', f'NAME = {name}')

        self.info(f'Preparing to run ensembles in {run_dir}')

        # Ensure that we create a unique task pool name for this using the
        # instance prefix `name`
        # check this first to ensure uniqueness of `name` parameter
        task_pool_name = f'{name}_ensemble_task_pool'
        self.create_task_pool(task_pool_name)

        # Grab the IPS config template to be used for all ensemble instances;
        # str to convert from pathlib.Path; harmless conversion if already a
        # Path.
        template_config_file = Path(template)
        if not template_config_file.exists():
            raise RuntimeError(f'Template file {template_config_file.absolute()} not found')
        template_config = ConfigObj(str(template))

        # Let's first "flatten" the hierarchical variables dict into a list
        # of lists of dicts, where the top-level of which contains the ensemble
        # instance name and associated parameters.
        instances = ipsutil.group_ensemble_variables_into_instances(variables, name)

        # save the variables on both disk and to the IPS Portal
        csv_out = Path(run_dir) / f'{name}__ensemble_variables.csv'
        ipsutil.ensemble_instances_to_csv(instances, csv_out)
        send_ensemble_instance_to_portal(name, csv_out)

        # For each coupled simulation instance
        for instance in instances:
            self.info(f'Adding ensemble instance {instance[0]} to queue')

            # Create the subdir based on `path_dir` and the ensemble ID, which
            # is stored as the first list element in `instance`
            working_dir = Path(run_dir) / instance[0]
            working_dir.mkdir(parents=True, exist_ok=True)
            self.debug(f'Working directory for instance {instance[0]} is {working_dir}')

            # Local log file for this ensemble instance
            log_file = working_dir / f'{instance[0]}.log'
            self.debug(f'Log file for instance {instance[0]} is {log_file}')

            # Make a bespoke config file for this simulation instance based
            # on the template. This means substituting all the "?" variables
            # in the template with the corresponding values found in
            # `variables`. The second `instance` list element contains the
            # variables that need to be substituted into the template.  We
            # copy the template because we will want to start fresh with each
            # instance, particularly because part of the error checking is to
            # ensure that all the variables have been assigned.  The first
            # instance element contains the ensemble instance name.
            simulation_filename = create_driver_config_file(deepcopy(template_config),
                                                            working_dir,
                                                            instance[1],
                                                            instance[0],
                                                            use_portal)
            self.debug(f'Simulation config file for instance {instance[0]} is '
                       f'{simulation_filename}')

            # Create the bespoke platform config file for this instance
            platform_filename = create_platform_config_file(instance[0],
                                                            working_dir,
                                                            cores_per_instance)
            self.debug(f'Platform config file for instance {instance[0]} is '
                       f'{platform_filename}')

            # Submit a task to run the simulation instance, which is another
            # IPS run pointed to that config file.
            args = [f'--simulation={simulation_filename}', f'--log={log_file}', f'--platform={platform_filename!s}']

            if self.fwk.logger.getEffectiveLevel() == logging.DEBUG:
                # If we're in debug mode, then also pass the debug flag.
                # May as well pass in the --verbose, too.
                args.insert(1, '--debug')
                args.insert(1, '--verbose')

            self.add_task(task_pool_name, instance[0], 1, working_dir, 'ips.py', *args)

        try:
            # Note that we *always* use Dask to run the ensemble tasks
            num_submitted = self.submit_tasks(
                task_pool_name,  # block=True,
                use_dask=True,
                dask_nodes=num_nodes,
                dask_ppw=cores_per_instance,
                oversubscribe=oversubscribe,
                hwthreads=hwthreads,
                # launch_interval=0.0,
                # use_shifter=False,
                # shifter_args=None,
                # dask_worker_plugin=None,
                # dask_worker_per_gpu=False
            )
            self.logger.info(f'Submitted {num_submitted} ensemble tasks')
        except Exception as e:
            self.critical(f'Got an exception running ensemble: {e!s}')
            traceback.print_exc()
        finally:
            exit_status = self.get_finished_tasks(task_pool_name)
            self.info(f'Finished tasks: {exit_status!s}')

            self.remove_task_pool(task_pool_name)

        return instances


class DVMPlugin(WorkerPlugin):
    def __init__(self, logger, oversubscribe=False, hwthreads=False):
        """
        Dask worker plugin to launch and manage an OpenMPI PRTE DVM on each
        worker node.

        :param logger: Logger object
        :param oversubscribe: Whether to allow oversubscription of nodes
            when launching the ensemble runs. Default is False.
        :param hwthreads: Whether to use hardware threads
        """
        super().__init__()

        self.logger = logger
        self.oversubscribe = oversubscribe
        self.hwthreads = hwthreads

    def setup(self, worker: Worker):
        """
        :param worker: Dask worker
        :param oversubscribe: Whether to allow oversubscription of nodes
            when launching the ensemble runs. Default is False.
        """
        if 'HWLOC_XMLFILE' in os.environ:
            # Remove HWLOC_XMLFILE to avoid issues with OpenMPI on Dask workers
            self.logger.debug('Removing HWLOC_XMLFILE environment variable for '
                              'Dask worker')
            del os.environ['HWLOC_XMLFILE']
        else:
            self.logger.debug('HWLOC_XMLFILE environment variable not set '
                              'for Dask worker')

        # Necessary to ensure the DVM "sees" all the resources to manage
        os.environ['PRTE_MCA_ras_slurm_use_entire_allocation'] = '1'

        self.worker = worker
        worker.logger = self.logger

        self.logger.info('Launching DVM')
        self.worker.dvm_uri_file = f'/tmp/dvm.uri.{os.getpid()}'
        command = [#'srun', '--mpi=pmix_v4', '-N', os.environ['SLURM_NNODES'], '--ntasks-per-node=1',
                   'prte', #'--no-daemonize',
                   '--report-uri', self.worker.dvm_uri_file]

        mapping_policy = 'core'  # by default bind to cores
        if self.hwthreads:
            # ... unless you want to bind to hardware threads
            self.logger.info('Binding to hardware threads')
            mapping_policy = 'hwtcpus'

        if self.oversubscribe:
            self.logger.info('Allowing oversubscription of nodes')
            mapping_policy += ':oversubscribe'

        # This environment variable is specific to OpenMPI's PRTE
        os.environ['PRTE_MCA_rmaps_default_mapping_policy'] = mapping_policy

        try:
            self.logger.debug(f'Executing command: {command!s}')
            self.worker.dvm_proc = subprocess.Popen(command,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.STDOUT)
        except Exception as e:
            print(f'Exception during setting up DVM: {e}')
            console.print(Traceback.from_exception(type(e), e, e.__traceback__))

            # If there was an exception, dump any stdout/stderr we have
            if hasattr(self.worker.dvm_proc, 'stdout'):
                print(self.worker.dvm_proc.stdout, file=sys.stdout, flush=True)
                print(self.worker.dvm_proc.stderr, file=sys.stderr, flush=True)

        # TODO What if there was a subprocess exception?

        ready = self.worker.dvm_proc.stdout.readline()
        self.logger.info(f'Ready Message : {ready}')
        print(f'Ready Message : {ready}', flush=True)

        with open(self.worker.dvm_uri_file, 'r') as f:
            self.worker.dvm_uri = f.readline()
            print(f'Read DVM URI: {self.worker.dvm_uri}', flush=True)
            self.logger.debug(f'Read DVM URI: {self.worker.dvm_uri}')

        os.environ['PMIX_SERVER_URI41'] = self.worker.dvm_uri


    def teardown(self, worker: Worker):
        self.logger.info(f'Shutting down DVM at {self.worker.dvm_uri}')
        command = ['pterm', '--dvm-uri', self.worker.dvm_uri]
        subprocess.call(command)
        self.worker.dvm_proc.terminate()
        self.worker.dvm_proc.kill()


class TaskPool:
    """
    Class to contain and manage a pool of tasks.
    """

    try:
        dask = __import__('dask')
        distributed = __import__('dask.distributed')
    except ImportError:
        dask = None
        distributed = None
    else:
        # `dask-scheduler` and `dask-worker` are deprecated in favor of `dask
        # scheduler` and `dask worker`
        dask = shutil.which('dask')
        dask_scheduler = [dask, 'scheduler']
        dask_worker = [dask, 'worker']

        shifter = shutil.which('shifter')

        IDLE_TIMEOUT = 60 * 10  # 10 minute default

    def __init__(self, name: str, services: ServicesProxy):
        self.dask_pool = False
        self.name = name
        self.services = services
        self.active_tasks = {}
        self.finished_tasks = {}
        self.queued_tasks: dict[str, Task] = {}
        self.blocked_tasks = {}
        self.serial_pool = True
        self.dask_sched_pid = None
        self.dask_sched_popen = None
        self.dask_workers_tid = None
        self.futures = None
        self.dask_scheduler_file = None
        self.dask_client = None
        self.worker_event_logfile = None

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

    def add_task(self, task_name: str, nproc: int, working_dir: str, binary: str, *args, **keywords):
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
                self.services.error('Program %s is not in path or is not executable', binary)
                raise Exception('Program %s is not in path or is not executable' % binary)
            else:
                self.services.binary_fullpath_cache[binary] = binary_fullpath

        keywords['keywords']['block'] = False

        self.serial_pool = self.serial_pool and (nproc == 1)
        self.queued_tasks[task_name] = Task(task_name, nproc, working_dir, binary_fullpath, *args, **keywords['keywords'])

    def submit_dask_tasks(
        self,
        block=True,
        dask_nodes=1,
        dask_ppw=None,
        use_shifter=False,
        shifter_args=None,
        dask_worker_plugin=None,
        dask_worker_per_gpu=False,
        oversubscribe=False,
        hwthreads=False,
    ):
        """Launch tasks in *queued_tasks* using dask.

        One dask worker will be started for each node unless
        dask_worker_per_gpu is True where one dask worker will be
        started for every GPU. So dask_node times GPUS_PER_NODE
        workers will be started.

        :param block: Unused, this will always return after tasks are submitted
        :type block: bool
        :param dask_nodes: Number of task nodes, default 1
        :type dask_nodes: int
        :param dask_ppw:  Number of processes per dask worker, default is PROCS_PER_NODE
            However, dask_ppw will be "cores per instance" if using ensembles,
            so will be `PROCS_PER_NODE // dask_ppw` to enforce that each dask
            worker will have multiple cores, hopefully articulated via DVM
            (i.e., prun will be invoked and will coordinate with the DVM to
            allocate multiple cores to each worker thread). Note that the DVM
            daemon will be started by the registered Dask worker plugin DVMPlugin.
        :type dask_ppw: int
        :param use_shifter:  Option to launch dask scheduler and workers in shifter container
        :type use_shifter: bool
        :param dask_worker_plugin: If provided this will be registered as a worker plugin with the dask client
        :type dask_worker_plugin: distributed.diagnostics.plugin.WorkerPlugin
        :param dask_worker_per_gpu: If true then a separate worker will be started for each GPU and binded to that GPU
        :type dask_worker_per_gpu: bool
        :param oversubscribe: Whether to allow oversubscription of nodes
            when launching the dask workers. Default is False.
        :type oversubscribe: bool
        :param hwthreads: Whether to use hardware threads
        :type hwthreads: bool

        FIXME consider having n processes instead of n threads given that we're
            likely running in a HPC context.
            See: https://distributed.dask.org/en/stable/efficiency.html#adjust-between-threads-and-processes

        :returns: number of tasks submitted
        """

        def _make_worker_args(num_workers: int, num_threads: int, use_shifter: bool, shifter_args=None):
            """Make Dask worker command line arguments.

            :param num_workers: Number of workers to start
            :param num_threads: Number of threads per worker
            :param use_shifter: If True, then use shifter to launch the worker
            :returns: list of command line arguments to pass to subprocess call
                to start a Dask worker
            """
            base_args = [
                *self.dask_worker,
                '--no-dashboard',
                '--no-nanny',
                '--scheduler-file',
                self.dask_scheduler_file,
                '--nworkers',
                str(num_workers),
                '--nthreads',
                str(num_threads),
            ]

            if use_shifter:  # insert shifter command and args if needed
                # This could be a string or a list of arguments.
                if shifter_args:
                    if isinstance(shifter_args, tuple) and shifter_args != ():
                        base_args[0:0] = shifter_args
                    elif isinstance(shifter_args, str) and shifter_args != '':
                        base_args.insert(0, shifter_args)
                base_args.insert(0, self.shifter)

            return base_args

        services: ServicesProxy = self.services

        # Note that we use the absolute path since at some point we may
        # be in a different directory, which means that we otherwise would
        # not be able to find the Dask scheduler file.
        self.dask_scheduler_file = Path('.').absolute() / f'{self.name}_dask_sched_{datetime.now().strftime("%Y%m%d%S")}.json'
        # self.dask_scheduler_file = os.path.join(os.getcwd(), f'{self.name}_dask_shed_{time.time()}.json')

        if use_shifter:
            if shifter_args:
                self.dask_sched_popen = subprocess.Popen(
                    [
                        self.shifter,
                        shifter_args,
                        *self.dask_scheduler,
                        '--no-dashboard',
                        '--no-jupyter',
                        '--no-show',
                        '--idle-timeout',
                        str(TaskPool.IDLE_TIMEOUT),
                        '--scheduler-file',
                        str(self.dask_scheduler_file),
                        '--port',
                        '0',
                    ]
                )
                self.dask_sched_pid = self.dask_sched_popen.pid
            else:
                self.dask_sched_popen = subprocess.Popen(
                    [
                        self.shifter,
                        *self.dask_scheduler,
                        '--no-dashboard',
                        '--no-jupyter',
                        '--no-show',
                        '--idle-timeout',
                        str(TaskPool.IDLE_TIMEOUT),
                        '--scheduler-file',
                        str(self.dask_scheduler_file),
                        '--port',
                        '0',
                    ]
                )
                self.dask_sched_pid = self.dask_sched_popen.pid

        else: # We are NOT using shifter
            try:
                args = [
                        *self.dask_scheduler,
                        '--no-dashboard',
                        '--no-jupyter',
                        '--no-show',
                        '--idle-timeout',
                        str(TaskPool.IDLE_TIMEOUT),
                        '--scheduler-file',
                        str(self.dask_scheduler_file),
                        '--port',
                        '0',
                    ]
                self.services.info(f'Scheduler args: {' '.join(args)}')
                self.dask_sched_popen = subprocess.Popen(args)
                self.dask_sched_pid = self.dask_sched_popen.pid
                self.services.info(f'Scheduler pid: '
                                   f'{self.dask_sched_popen.pid}')
            except Exception as e:
                self.services.critical(f'Exception while starting Dask '
                                       f'scheduler: {e!s}')
                console.print_exception(show_locals=True)
                # TODO better error handling than just re-raising the exception
                raise

        dask_nodes = 1 if dask_nodes is None else dask_nodes
        if services.get_config_param('MPIRUN') == 'eval':
            # TODO Why?
            dask_nodes = 1

        # By default we should have as many threads as there are
        # processors on the node, which is what PROCS_PER_NODE should be set
        # to.  However, if the user has specified dask_ppw, then we will
        # divide the number of processors by that number to get the number
        # of threads per Dask worker.  If dask_ppw is None, then we will
        # use the number of processors per node.
        nthreads = services.get_config_param('PROCS_PER_NODE')

        if dask_worker_per_gpu:
            gpn = services.get_config_param('GPUS_PER_NODE')
            dask_nodes *= gpn
            nthreads = dask_ppw if dask_ppw else services.get_config_param('PROCS_PER_NODE') // gpn
            task_ppn = gpn
            task_gpp = 1
        else:
            # The number of threads per Dask worker is the number of processors
            # on that node divided by the cores per instance, which we're
            # using dask_ppp for.  (Which suggests that we need to change the
            # signature for this function to make that clearer, or to allow a
            # user to override this and specify *exactly* how many cores per
            # Dask worker they want.)
            # nthreads = dask_ppw if dask_ppw else services.get_config_param("PROCS_PER_NODE")
            cores_per_node = services.get_config_param('PROCS_PER_NODE')
            if not cores_per_node or cores_per_node < 1:
                # if PROCS_PER_NODE is missing, fall back on CORES_PER_NODE
                cores_per_node = services.get_config_param('CORES_PER_NODE')

            if dask_ppw is not None:
                self.services.debug(f'Using {dask_ppw} processes per Dask worker via dask_ppw argument')
                print(f'Using {dask_ppw} processes per Dask worker via dask_ppw argument', flush=True)
                nthreads = cores_per_node // dask_ppw
            else:
                nthreads = cores_per_node

            task_ppn = 1  # TODO Chase down the exact meaning of this.
            task_gpp = 0

        # Reality check; nthreads should be at least 1
        nthreads = 1 if nthreads is None or nthreads == 0 else nthreads

        self.services.debug(f'Number of threads: {nthreads}')
        print(f'(submit_dask_tasks: Number of threads: {nthreads})', flush=True)

        if dask_ppw is not None:
            self.services.debug(f'Using {dask_ppw} processes per Dask worker via dask_ppw argument')
            # FIXME Redundant print since debug() appears to be ignored.
            print(f'Using {dask_ppw} processes per Dask worker via dask_ppw argument', flush=True)
        else:
            dask_ppw = int(services.get_config_param('PROCS_PER_NODE'))
            self.services.debug(f'using {services.get_config_param("PROCS_PER_NODE")} processes per Dask worker from platform config PROCS_PER_NODE')
        self.services.info(f'Threads per Dask worker is {nthreads}')

        # --nprocs was removed in version 2022.10.0 and replaced with --nworkers
        # nworkers = '--nworkers' if tuple(map(int, self.distributed.__version__.split('.'))) >= (2022, 10, 0) else '--nprocs'

        workers_cmd_line = _make_worker_args(num_workers=1, num_threads=nthreads, use_shifter=use_shifter, shifter_args=shifter_args)

        self.services.debug(f'Dask workers command line: {workers_cmd_line}')

        self.dask_workers_tid = services.launch_task(dask_nodes, os.getcwd(), *workers_cmd_line, task_ppn=task_ppn, task_gpp=task_gpp)

        self.services.debug(f'Dask scheduler pid: {self.dask_sched_popen.pid}')

        self.dask_client = Client(scheduler_file=self.dask_scheduler_file)
        self.services.debug(f'Dask client: {self.dask_client!s}')

        # And logging done via the dask workers will be forwarded to the root
        # logger so that it can be captured by the services.
        self.dask_client.forward_logging()

        if dask_worker_plugin is not None:
            # TODO But what if there is more than one worker plugin?
            # TODO And what about scheduler plugins?
            self.dask_client.register_plugin(dask_worker_plugin)

        # Regardless of any other worker plugins, we need this plugin to setup
        # the DVM for the workers so that OpenMPI can work properly.
        self.dask_client.register_plugin(DVMPlugin(logger=services.logger,
                                                   oversubscribe=oversubscribe,
                                                   hwthreads=hwthreads))

        try:
            file_id = str(self.services._portal_runid) if self.services._portal_runid > 0 else self.services._fallback_portal_runid
            self.worker_event_logfile = services.sim_name + '_' + file_id + '_' + self.name + '_{}.json'
            self.services.debug(f'Worker event log file: {self.worker_event_logfile}')
        except KeyError:
            # USE_PORTAL == False
            self.worker_event_logfile = None

        launch.__module__ = '__main__'
        self.futures = []
        for task_name, task in self.queued_tasks.items():
            self.services.debug(f'Submitting task {task_name} to dask client with {dask_ppw} cores per worker')
            self.services.debug(f'Task {task_name} working dir: {task.working_dir}')
            self.services.debug(f'Task args: {task.args} keywords: {task.keywords}')
            self.futures.append(
                self.dask_client.submit(
                    launch,
                    task.binary,
                    task_name,
                    task.working_dir,
                    *task.args,
                    **task.keywords,
                    key=task_name,
                    cpus_per_proc=dask_ppw,
                    worker_event_logfile=self.worker_event_logfile,
                )
            )
        self.active_tasks = self.queued_tasks
        self.queued_tasks = {}
        return len(self.futures)

    def submit_tasks(
        self,
        block=True,
        use_dask=False,
        dask_nodes=1,
        dask_ppw=None,
        launch_interval=0.0,
        use_shifter=False,
        shifter_args=None,
        dask_worker_plugin=None,
        dask_worker_per_gpu=False,
        oversubscribe=False,
        hwthreads=False,
    ):
        """Launch tasks in *queued_tasks*.  Finished tasks are handled before
        launching new ones.  If *block* is ``True``, the number of
        tasks submitted is returned after all tasks have been launched
        and completed.  If *block* is ``False`` the number of tasks
        that can immediately be launched is returned.

        If ``use_dask==True`` then the tasks are launched with
        :meth:`submit_dask_tasks`. One dask worker will be started for
        each node unless dask_worker_per_gpu is True where one dask
        worker will be started for every GPU. So dask_node times
        GPUS_PER_NODE workers will be started.

        :param block: If True then wait for task to complete, default True
        :type block: bool
        :param use_dask: If True then use dask to launch tasks, default False
        :type use_dask: bool
        :param dask_nodes: Number of task nodes, only used it ``use_dask==True``
        :type dask_nodes: int
        :param dask_ppw:  Number of processes per dask worker, default is PROCS_PER_NODE, only used it ``use_dask==True``
        :type dask_ppw: int
        :param launch_internal: time to wait between launching tasks, default 0.0
        :type launch_internal: float
        :param use_shifter:  Option to launch dask scheduler and workers in shifter container
        :type use_shifter: bool
        :param shifter_args:  Optional arguments added to shifter when launching dask scheduler and workers
        :type shifter_args: str
        :param dask_worker_plugin: If provided this will be registered as a worker plugin with the dask client
        :type dask_worker_plugin: distributed.diagnostics.plugin.WorkerPlugin
        :param dask_worker_per_gpu: If true then a separate worker will be started for each GPU and binded to that GPU
        :type dask_worker_per_gpu: bool
        :returns: number of tasks submitted
        :param oversubscribe: If True then pass the oversubscribe option to
            mpirun when launching dask workers
        :type oversubscribe: bool
        :param hwthreads: If True then use hardware threads when launching
            tasks. Default is False.
        :type hwthreads: bool
        """

        if use_dask:
            if TaskPool.dask and TaskPool.distributed and self.serial_pool:
                self.dask_pool = True
                if use_shifter and not self.shifter:
                    self.services.error('Requested to run dask within shifter but shifter not available')
                    raise RuntimeError('shifter not found')
                else:
                    return self.submit_dask_tasks(
                        block, dask_nodes, dask_ppw, use_shifter, shifter_args, dask_worker_plugin, dask_worker_per_gpu, oversubscribe, hwthreads
                    )
            elif not TaskPool.dask or not TaskPool.distributed:
                raise RuntimeError('Requested use_dask but cannot because import dask or distributed failed')
            elif not self.serial_pool:
                self.services.warning('Requested use_dask but cannot because multiple processors requested')

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

    def _shutdown_dask(self):
        """
        Shut down the dask client, scheduler, and workers.

        Side effect is setting self.dask_sched_pid and self.dask_client
        to None.

        :returns: None
        """
        # Gently release any pending futures
        for f in self.futures:
            f.release()

        if self.dask_client is not None:
            # Shutdown handles ending client, scheduler, and workers
            self.dask_client.shutdown()

            # TODO a more gentle way to shutdown:
            #  1. self.dask_client.close()
            #  2. terminate the workers (we should use Popen objects,
            #  so worker_popen.terminate())
            #  3. terminate the scheduler via self.dask_sched_popen.terminate()

            # Set these to None since we check for that for any
            # subsequent Dask tasks
            self.dask_sched_pid = None
            self.dask_client = None

            # No need for any of this nonsense:
            # self.dask_client.close()
        #     self.dask_client = None
        # if self.dask_sched_pid is not None:
        #     try:
        #         os.kill(self.dask_sched_pid, signal.SIGTERM)
        #     except OSError as e:
        #         self.services.exception(f'Error shutting down dask scheduler: {e}')
        #     self.dask_sched_pid = None
        #
        # time.sleep(1)  # Give time for the scheduler to shut down

    def get_dask_finished_tasks_status(self):
        """Return a dictionary of exit status values for all dask tasks that
        have finished since the last time finished tasks were polled.

        This function *also* shuts down the dask client.  (FIXME The fate of
        the Dask scheduler and workers is unknown.)

        It also, as yet another side-effect if it sees there's an associated
        self.worker_event_logfile.  If there is one it will send monitor events
        for each record found in that file.  It will then remove these log
        files.

        TODO I recommend possibly splitting this into three different, focused
         functions.  One for gathering the exit statuses from all workers.
         Another for shutting down Dask, which means shutting down the client,
         scheduler, *and* workers, not just the client.  (Though the scheduler
         and workers will eventually expire due to timeouts.) And another for
         creating events from Dask log messages.  (With a boolean argument to
         denote whether these log files should be deleted after the fact.  I.e.,
         the practitioner may want to look at those even if they're emitted
         as IPS events.)

        This also presumes that the dask workers will return an exit status,
        presumably of related subprocess calls.

        FIXME What if we have other Dask tasks that do not return an
         exit status?

        :return: dict mapping task name to exit status
        :rtype: dict
        """
        if self.dask_client is None:
            # FIXME How does this happen and is it ok when it does?
            self.services.warning('No dask client in call to finished tasks status')
            return {}

        if self.futures is None:
            # FIXME How does this happen and is it ok when it does?
            self.services.warning('No futures available in call to finished tasks status')
            self._shutdown_dask()

            return {}

        self.services.debug('get_dask_finished_tasks_status: before gather()')
        result = self.dask_client.gather(self.futures)
        self.services.debug('get_dask_finished_tasks_status: after gather()')

        # If we don't have a result, then there were no tasks to gather.
        if result is None:
            self.services.warning('No futures available in call to finished ')
            self._shutdown_dask()
            return {}
        else:
            self.services.debug(f'get_dask_finished_tasks_status: have {len(result)} futures')

        worker_names = [''.join(c for c in worker['name'] if c.isalnum()) for worker in self.dask_client.scheduler_info()['workers'].values()]
        self.services.debug(f'get_dask_finished_tasks_status: worker_names: {worker_names!s}')

        # NOTE: You may get an exception stack trace from Dask, this is currently not believed to cause an issue.
        # We no longer need Dask running, so shut it down.
        self.services.debug(f'get_dask_finished_tasks_status: before _shutdown_dask()')
        self._shutdown_dask()
        self.services.debug(f'get_dask_finished_tasks_status: after _shutdown_dask()')

        if self.worker_event_logfile is not None:
            self.services.debug(f'get_dask_finished_tasks_status: worker_event_logfile: '
                       f'{self.worker_event_logfile!s}')
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
                    self.services._send_monitor_event(**event)
            except Exception as e:
                # If it fails for any other reason, make sure we can continue
                self.services.exception('Error while reading dask worker log files: %s', str(e))
            else:
                for worker in worker_names:
                    if os.path.isfile(self.worker_event_logfile.format(worker)):
                        os.remove(self.worker_event_logfile.format(worker))

        self.finished_tasks = {}
        self.active_tasks = {}
        self.services.wait_task(self.dask_workers_tid)
        self.dask_scheduler_file = None
        self.dask_workers_tid = None
        self.dask_sched_pid: Optional[int] = None
        self.dask_sched_popen = None
        self.dask_pool = False
        self.serial_pool = True

        if result is not None:
            self.services.debug('get_dask_finished_tasks_status: have result')
            # FIXME assumes that we can convert `result` into a dict, which
            #  is doubtful.
            return dict(result)

        self.services.debug('get_dask_finished_tasks_status: no result, returning None')

        return result  # which will be none

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
                for task_id in self.active_tasks:
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

    def __init__(self, task_name: str, nproc: int, working_dir: str, binary: str, *args, **keywords):
        self.name = task_name
        self.nproc = int(nproc)
        self.working_dir = working_dir
        self.binary = binary
        self.args = [str(a) for a in args] if args else args
        self.keywords = keywords
        self.exit_status = None
