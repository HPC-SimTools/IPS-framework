# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
from math import ceil
from . import messages, configurationManager
from .ipsExceptions import BlockedMessageException, \
    IncompleteCallException, \
    InsufficientResourcesException, \
    BadResourceRequestException, \
    ResourceRequestMismatchException
from .ipsutil import which


class TaskManager:
    """
    The task manager is responsible for facilitating component method
    invocations, and the launching of tasks.
    """
    # TM __init__

    def __init__(self, fwk):
        # ref to framework
        self.fwk = fwk
        self.event_mgr = None
        self.data_mgr = None
        self.resource_mgr = None
        self.config_mgr = None
        self.comp_registry = configurationManager.ComponentRegistry()
        self.service_methods = ['init_call',
                                'launch_task',
                                # 'launchTask',   --- deprecated
                                'wait_call',
                                'init_task',
                                'init_task_pool',
                                'finish_task']
        # **** this si where service methods are registered
        self.fwk.register_service_handler(self.service_methods,
                                          getattr(self, 'process_service_request'))
        self.task_map = {}
        self.task_launch_cmd = ''

        # table of currently running tasks
        self.curr_task_table = {}
        # nextCall
        self.next_call_id = 1
        self.next_task_id = 1
        self.outstanding_calls = {}
        self.finished_calls = {}
        self.mpicmd = None  # USed only for CCM on edison

    # this is where messages are received and then something smart happens
    def process_service_request(self, msg):
        """
        Invokes the appropriate public data manager method for the component
        specified in *msg*.  Return method's return value.
        """
        self.fwk.debug('Task Manager received message: %s', str(msg.__dict__))
        method = getattr(self, msg.target_method)
        retval = method(msg)
        return retval

    # TM initialize
    def initialize(self, data_mgr, resource_mgr, config_mgr):
        """
        Initialize references to other managers and key values from
        configuration manager.
        """
        self.event_mgr = None  # eventManager(self)
        self.data_mgr = data_mgr
        self.resource_mgr = resource_mgr
        self.config_mgr = config_mgr
        self.host = self.config_mgr.get_platform_parameter('HOST')
        self.node_alloc_mode = self.config_mgr.get_platform_parameter('NODE_ALLOCATION_MODE')
        try:
            self.task_launch_cmd = self.config_mgr.get_platform_parameter('MPIRUN')
        except Exception:
            print('Error accessing platform parameter MPIRUN')
            raise

        # do later - subscribe to events, set up event publishing structure
        # publish "TM initialized" event

    def get_call_id(self):
        """
        Return a new call id
        """
        retval = self.next_call_id
        self.next_call_id = self.next_call_id + 1
        return retval

    def get_task_id(self):
        """
        Return a new task id
        """
        retval = self.next_task_id
        self.next_task_id = self.next_task_id + 1
        return retval

    def printCurrTaskTable(self):
        """
        Prints the task table pretty-like.
        """
        ctt = self.curr_task_table
        for c, i in list(ctt.items()):
            print(c)
            for k, v in list(i.items()):
                print("   ", k, "=", v)
            print("------")
        print("=====================")

    # TM call
    def init_call(self, init_call_msg, manage_return=True):
        r"""
        Creates and sends a :py:obj:`messages.MethodInvokeMessage` from
        the calling component
        to the target component.  If *manage_return* is ``True``, a record is
        added to *outstanding_calls*.  Return call id.

        Message args:

          0. method_name

          1. \+ arguments to be passed on as method arguments.
        """
        callee_id = init_call_msg.target_comp_id
        method_name = init_call_msg.args[0]
        args = init_call_msg.args[1:]
        keywords = init_call_msg.keywords
        caller_id = init_call_msg.sender_id
        call_id = self.get_call_id()
        self.fwk.debug('TM:init_call(): %s %s %s %s',
                       caller_id, callee_id, method_name, str(args))
        invoke_msg = messages.MethodInvokeMessage(self.fwk.component_id,
                                                  callee_id,
                                                  call_id,
                                                  method_name, *args, **keywords)
        invocation_q = self.comp_registry.getComponentArtifact(callee_id,
                                                               'invocation_q')
        invocation_q.put(invoke_msg)
        if manage_return:
            self.outstanding_calls[call_id] = (caller_id, None)
        return call_id

    def return_call(self, response_msg):
        """
        Handle the response message generated by a component in response
        to a method invocation on that component.

        *reponse_msg* is expected to be of type :py:obj:`messages.MethodResultMessage`
        """
        call_id = response_msg.call_id
        caller_id = self.outstanding_calls[call_id][0]
        self.fwk.debug('TM:call_return() call_id = %s caller_id = %s', call_id, caller_id)
        self.finished_calls[call_id] = (caller_id, response_msg)
        del self.outstanding_calls[call_id]

    def wait_call(self, wait_msg):
        """
        Determine if the call has finished.  If finished, return any data or
        errors.  If not finished raise the appropriate blocking or nonblocking
        exception and try again later.

        *wait_msg* is expected to be of type :py:obj:`messages.ServiceRequestMessage`

        Message args:

        0. *call_id*: call id for which to wait

        1. *blocking*: determines the wait is blocking or not
        """
        call_id = wait_msg.args[0]
        blocking = wait_msg.args[1]
        self.fwk.debug('TM:wait_call() call_id = %s', call_id)
        if call_id in self.finished_calls:
            response_msg = self.finished_calls[call_id][1]
            del self.finished_calls[call_id]
            if response_msg.status == messages.Message.FAILURE:
                raise Exception(response_msg.args[0])
            else:
                return response_msg.args
        if not blocking:
            raise IncompleteCallException(call_id)
        else:
            raise BlockedMessageException(wait_msg, '***call %s not finished' % call_id)

    def init_task(self, init_task_msg):
        r"""
        Allocate resources needed for a new task and build the task
        launch command using the binary and arguments provided by
        the requesting component.  Return launch command to component via
        :py:obj:`messages.ServiceResponseMessage`.  Raise exception if task
        can not be launched at this time (:py:exc:`ipsExceptions.BadResourceRequestException`, :py:exc:`ipsExceptions.InsufficientResourcesException`).

        *init_task_msg* is expected to be of type :py:obj:`messages.ServiceRequestMessage`

        Message args:

        0. *nproc*: number of processes the task needs

        1. *binary*: full path to the executable to launch

        # SIMYAN: added this to deal with the component directory change
        2. *working_dir*: full path to directory where the task will be launched

        3. *tppn*: processes per node for this task.  (0 indicates that the default ppn is used.)

        4. *block*: whether or not to wait until the task can be launched.

        5. *wnodes*: ``True`` for whole node allocation, ``False`` otherwise.

        6. *wsocks*: ``True`` for whole socket allocation, ``False`` otherwise.

        7. \+ *cmd_args*: any arguments for the executable
        """
        caller_id = init_task_msg.sender_id
        nproc = int(init_task_msg.args[0])
        binary = init_task_msg.args[1]
        # SIMYAN: working_dir stored
        working_dir = init_task_msg.args[2]
        tppn = int(init_task_msg.args[3])  # task processes per node
        block = init_task_msg.args[4]  # Block waiting for available resources
        wnodes = init_task_msg.args[5]
        wsocks = init_task_msg.args[6]

        # SIMYAN: increased arguments
        cmd_args = init_task_msg.args[7:]
        # handle for task related things
        task_id = self.get_task_id()

        try:
            retval = self.resource_mgr.get_allocation(caller_id,
                                                      nproc,
                                                      task_id,
                                                      wnodes,
                                                      wsocks,
                                                      task_ppn=tppn)
            self.fwk.debug('RM: get_allocation() returned %s', str(retval))
            partial_node = retval[0]
            if partial_node:
                (nodelist, corelist, ppn, max_ppn, accurateNodes) = retval[1:]
            else:
                (nodelist, ppn, max_ppn, accurateNodes) = retval[1:]
        except InsufficientResourcesException:
            if block:
                raise BlockedMessageException(init_task_msg, '***%s waiting for %d resources' %
                                              (caller_id, nproc))
            else:
                raise
        except BadResourceRequestException as e:
            self.fwk.error("There has been a fatal error, %s requested %d too many processors in task %d",
                           caller_id, e.deficit, e.task_id)
            raise
        except ResourceRequestMismatchException as e:
            self.fwk.error("There has been a fatal error, %s requested too few processors per node to launch task %d (requested: procs = %d, ppn = %d)",
                           caller_id, e.task_id, e.nproc, e.ppn)
            raise
        except Exception:
            raise

        # SIMYAN: moved up a few lines and ret_data, node_file added
        self.curr_task_table[task_id] = {'component': caller_id,
                                         'status': 'init_task',
                                         'binary': binary,
                                         'nproc': nproc,
                                         'args': cmd_args,
                                         'launch_cmd': None,
                                         'env_update': None,
                                         'ret_data': None,
                                         'node_file': None}
        if partial_node:
            nodes = ','.join(nodelist)
            (cmd, env_update) = self.build_launch_cmd(nproc, binary, cmd_args,
                                                      working_dir, ppn,
                                                      max_ppn, nodes,
                                                      accurateNodes,
                                                      partial_node, task_id,
                                                      core_list=corelist)
        else:
            if accurateNodes:
                nodes = ','.join(nodelist)
            else:
                nodes = ''
            (cmd, env_update) = self.build_launch_cmd(nproc, binary, cmd_args,
                                                      working_dir, ppn,
                                                      max_ppn, nodes,
                                                      accurateNodes,
                                                      False, task_id)
        task_data = self.curr_task_table[task_id]
        task_data['launch_cmd'] = cmd
        task_data['env_update'] = env_update
        return (task_id, cmd, env_update)

    def build_launch_cmd(self, nproc, binary, cmd_args, working_dir, ppn,
                         max_ppn, nodes, accurateNodes, partial_nodes,
                         task_id, core_list=''):
        """
        Construct task launch command to be executed by the component.

         * nproc - number of processes to use
         * binary - binary to launch
         * cmd_args - additional command line arguments for the binary
         * working_dir - full path to where the executable will be launched
         * ppn - processes per node value to use
         * max_ppn - maximum possible ppn for this allocation
         * nodes - comma separated list of node ids
         * accurateNodes - if ``True``, launch on nodes in *nodes*, otherwise the parallel launcher determines the process placement
         * partial_nodes - if ``True`` and *accurateNodes* and *task_launch_cmd* == 'mpirun',
               a host file is created specifying the exact placement of processes on cores.
         * core_list - used for creating host file with process to core mappings
        """
        # set up launch command
        env_update = None
        nproc_flag = ''
        smp_node = len(self.resource_mgr.nodes) == 1

        if self.task_launch_cmd == 'eval':
            # cmd = binary
            if len(cmd_args) > 0:
                cmd_args = ' '.join(cmd_args)
                cmd = ' '.join([binary, cmd_args])
            else:
                cmd = binary
            return cmd, env_update

        # -------------------------------------
        # mpirun
        # -------------------------------------
        elif self.task_launch_cmd == 'mpirun':
            version = self.config_mgr.get_platform_parameter('MPIRUN_VERSION').upper()
            if version.startswith("OPENMPI"):
                if version == 'OPENMPI-DVM':
                    mpi_binary = 'prun'
                    smp_node = False
                else:  # VERSION = OPENMPI_GENERIC
                    mpi_binary = 'mpirun'
                # Find and cache full path to launch executable
                if not self.mpicmd:
                    self.mpicmd = which(mpi_binary)
                mpicmd = self.mpicmd
                if not mpicmd:
                    raise Exception('Missing %s command in $PATH' % (mpi_binary))

                nproc_flag = '-np'
                ppn_flag = '-npernode'
                host_select = '-H'
                if smp_node or mpi_binary == 'prun':
                    cmd = ' '.join([mpicmd,
                                    nproc_flag, str(nproc)])
                else:
                    cmd = ' '.join([mpicmd,
                                    nproc_flag, str(nproc),
                                    ppn_flag, str(ppn)])
                cmd = f"{cmd} -x PYTHONPATH"  # Propagate PYTHONPATH to compute nodes
                if accurateNodes:
                    cmd = ' '.join([cmd, host_select, nodes])
            elif version == 'SGI':
                if accurateNodes:
                    core_dict = {}
                    ppn_groups = {}
                    num_cores = self.resource_mgr.cores_per_socket
                    for (n, cl) in core_list:
                        core_dict.update({n: cl})
                        if len(cl) in list(ppn_groups.keys()):
                            ppn_groups[len(cl)].append(n)
                        else:
                            ppn_groups.update({len(cl): [n]})
                    cmdlets = []
                    envlets = []
                    bin_n_args = ' '.join([binary, *cmd_args])
                    for p, ns in list(ppn_groups.items()):
                        cmdlets.append(' '.join([','.join(ns), str(p),
                                                 bin_n_args]))
                        el_node = []
                        for n in ns:
                            el_tmp = []
                            for k in core_dict[n]:
                                s, c = k.split(':')
                                s = int(s)
                                c = int(c)
                                el_tmp.append(str(s * num_cores + c))
                            el_node.append(','.join(el_tmp))
                        envlets.append(':'.join(el_node))
                    cmd = self.task_launch_cmd + ' ' + ' : '.join(cmdlets)
                    env_update = {'MPI_DSM_CPULIST': ':'.join(envlets)}
                    return cmd, env_update
                else:
                    cmd = ' '.join([self.task_launch_cmd, str(ppn), binary,
                                    ' '.join(cmd_args)])

        # --------------------------------------
        # mpiexec (MPICH variants)
        # --------------------------------------
        elif self.task_launch_cmd == 'mpiexec':
            nproc_flag = '-n'
            ppn_flag = '-npernode'
            if smp_node:
                cmd = ' '.join([self.task_launch_cmd, nproc_flag, str(nproc)])
            elif self.host == 'iter':
                cfg_fname = ".node_config_" + str(task_id)
                cfg_fname = os.path.join(working_dir, cfg_fname)
                cfg_file = open(cfg_fname, 'w')
                cmd_args = ' '.join(cmd_args)
                node_command = ' '.join([binary, cmd_args])
                node_spec = ''
                if partial_nodes:
                    for (node, cores) in core_list:
                        node_spec += ('%s ' % (node)) * len(cores)
                else:
                    for node in nodes.split(' ,'):
                        node_spec += ('%s ' % (node)) * ppn
                print('%s: %s' % (node_spec, node_command), file=cfg_file)
                config_option = '-config=' + cfg_fname
                cmd = ' '.join([self.task_launch_cmd, config_option])
                self.curr_task_table[task_id]['node_file'] = cfg_fname
                return cmd, env_update
            elif accurateNodes:  # Need to assign tasks to nodes explicitly
                host_select = '--host ' + nodes
                cmd = ' '.join([self.task_launch_cmd, host_select,
                                nproc_flag, str(nproc), ppn_flag,
                                str(ppn)])
            else:
                cmd = ' '.join([self.task_launch_cmd, nproc_flag,
                                str(nproc), ppn_flag, str(ppn)])
        # ------------------------------------
        # aprun (Cray parallel launch)
        # ------------------------------------
        elif self.task_launch_cmd == 'aprun':
            nproc_flag = '-n'
            ppn_flag = '-N'
            cpu_assign_flag = '-cc'
            by_numanode_flag = '-S'
            if self.host in ['hopper', 'edison']:
                num_numanodes = self.resource_mgr.sockets_per_node
                num_cores = self.resource_mgr.cores_per_node
                if accurateNodes:
                    nlist_flag = '-L'
                    num_nodes = len(nodes.split(','))
                    ppn = int(ceil(float(nproc) / num_nodes))
                    per_numa = int(ceil(float(ppn) / num_numanodes))
                    if per_numa == num_cores / num_numanodes:

                        cmd = ' '.join([self.task_launch_cmd,
                                        nproc_flag, str(nproc),
                                        ppn_flag, str(ppn),
                                        nlist_flag, nodes])
                    else:
                        if num_nodes > 1:
                            ppn = per_numa * num_numanodes
                        if nproc < ppn:
                            ppn = nproc
                        cmd = ' '.join([self.task_launch_cmd,
                                        nproc_flag, str(nproc),
                                        ppn_flag, str(ppn),
                                        by_numanode_flag, str(per_numa),
                                        nlist_flag, nodes])
                else:
                    num_nodes = int(ceil(float(nproc) / ppn))
                    ppn = int(ceil(float(nproc) / num_nodes))
                    per_numa = int(ceil(float(ppn) / num_numanodes))
                    if per_numa == self.resource_mgr.cores_per_node / self.resource_mgr.sockets_per_node:

                        cmd = ' '.join([self.task_launch_cmd,
                                        nproc_flag, str(nproc),
                                        ppn_flag, str(ppn)])
                    else:
                        if num_nodes > 1:
                            ppn = per_numa * num_numanodes
                        if nproc < ppn:
                            ppn = nproc
                        cmd = ' '.join([self.task_launch_cmd,
                                        nproc_flag, str(nproc),
                                        ppn_flag, str(ppn),
                                        by_numanode_flag, str(per_numa)])
            else:
                if accurateNodes:
                    nlist_flag = '-L'
                    cmd = ' '.join([self.task_launch_cmd,
                                    nproc_flag, str(nproc),
                                    ppn_flag, str(ppn),
                                    nlist_flag, nodes])
                else:
                    cmd = ' '.join([self.task_launch_cmd,
                                    nproc_flag, str(nproc),
                                    cpu_assign_flag,
                                    '%d-%d' % (max_ppn - 1, max_ppn - int(ppn)),
                                    ppn_flag, str(ppn)])
        # ------------------------------------
        # numactl (single process launcher)
        # ------------------------------------
        elif self.task_launch_cmd == 'numactl':
            if accurateNodes and partial_nodes:
                proc_flag = '--physcpubind='
                procs = ''
                for p in core_list:
                    procs = ','.join([k.split(':')[1] for k in p[1]])
                proc_flag += procs
            else:
                self.fwk.warning('numactl needs accurateNodes')
                proc_flag = ''
            cmd = ' '.join([self.task_launch_cmd,
                            proc_flag])
        elif self.task_launch_cmd == 'srun':
            nproc_flag = '-n'
            nnodes_flag = '-N'
            num_nodes = len(nodes.split(','))
            cmd = ' '.join([self.task_launch_cmd, nnodes_flag,
                            str(num_nodes), nproc_flag, str(nproc)])
        else:
            self.fwk.exception("invalid task launch command.")
            raise "invalid task launch command."

        cmd_args = ' '.join(cmd_args)
        cmd = ' '.join([cmd, binary, cmd_args])

        return cmd, env_update

    def init_task_pool(self, init_task_msg):
        """
        Allocate resources needed for a new task and build the task
        launch command using the binary and arguments provided by
        the requesting component.

        *init_task_msg* is expected to be of type :py:obj:`messages.ServiceRequestMessage`

        Message args:

        0. *task_dict*: dictionary of task names and objects
        """
        caller_id = init_task_msg.sender_id
        task_dict = init_task_msg.args[0]
        ret_dict = {}
        for task_name in list(task_dict.keys()):
            # handle for task related things
            task_id = self.get_task_id()
            (nproc, working_dir, binary, cmd_args, tppn, wnodes, wsocks) = task_dict[task_name]

            try:
                retval = self.resource_mgr.get_allocation(caller_id,
                                                          nproc,
                                                          task_id,
                                                          wnodes, wsocks,
                                                          task_ppn=tppn)
                self.fwk.debug('RM: get_allocation() returned %s', str(retval))
                partial_node = retval[0]
                if partial_node:
                    (nodelist, corelist, ppn, max_ppn, accurateNodes) = retval[1:]
                else:
                    (nodelist, ppn, max_ppn, accurateNodes) = retval[1:]

            except InsufficientResourcesException:
                continue
            except BadResourceRequestException as e:
                self.fwk.error("There has been a fatal error, %s requested %d too many processors in task %d",
                               caller_id, e.deficit, e.task_id)
                for (task_id, cmd) in list(ret_dict.values()):
                    self.resource_mgr.release_allocation(task_id, -1)
                    del self.curr_task_table[task_id]
                raise
            except ResourceRequestMismatchException as e:
                self.fwk.error("There has been a fatal error, %s requested too few processors per node to launch task %d (request: procs = %d, ppn = %d)",
                               caller_id, e.task_id, e.nproc, e.ppn)
                for (task_id, cmd) in list(ret_dict.values()):
                    self.resource_mgr.release_allocation(task_id, -1)
                    del self.curr_task_table[task_id]
                raise
            except Exception:
                self.fwk.exception('TM:init_task_pool(): Allocation exception')
                raise

            if partial_node:
                nodes = ','.join(nodelist)
                (cmd, env_update) = self.build_launch_cmd(nproc, binary,
                                                          cmd_args,
                                                          working_dir, ppn,
                                                          max_ppn, nodes,
                                                          accurateNodes,
                                                          partial_node,
                                                          task_id,
                                                          core_list=corelist)
            else:
                if accurateNodes:
                    nodes = ','.join(nodelist)
                else:
                    nodes = ''
                (cmd, env_update) = self.build_launch_cmd(nproc, binary,
                                                          cmd_args,
                                                          working_dir,
                                                          ppn, max_ppn, nodes,
                                                          accurateNodes, False,
                                                          task_id)

            self.curr_task_table[task_id] = {'component': caller_id,
                                             'status': 'init_task',
                                             'binary': binary,
                                             'nproc': nproc,
                                             'args': cmd_args,
                                             'launch_cmd': cmd,
                                             'env_update': env_update,
                                             'ret_data': None}
            ret_dict[task_name] = (task_id, cmd, env_update)
        return ret_dict

    def finish_task(self, finish_task_msg):
        """
        Cleanup after a task launched by a component terminates

        *finish_task_msg* is expected to be of type :py:obj:`messages.ServiceRequestMessage`

        Message args:

        0. *task_id*: task id of finished task

        1. *task_data*: return code of task
        """
        task_id = finish_task_msg.args[0]
        task_data = finish_task_msg.args[1]
        try:
            self.resource_mgr.release_allocation(task_id, task_data)
            del self.curr_task_table[task_id]
        except Exception:
            print('Error finishing task ', task_id)
            raise
        return 0
