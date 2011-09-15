# local version
import sys
import os
import re
import string
import time
from math import ceil
from socket import gethostname
from ipsExceptions import InsufficientResourcesException, \
     BadResourceRequestException, \
     NonexistentResourceException, \
     AllocatedNodeDownException, \
     ReleaseMismatchException, \
     ResourceRequestMismatchException
from ips_es_spec import eventManager
from resourceHelper import getResourceList
from node_structure import Node
# import things to use event service
#from event_service_spec import PublisherEventService,SubscriberEventService,EventListener,Topic,EventServiceException

#import resource helper code


class ResourceManager(object):
    """
    The resource manager is responsible for detecting the resources allocated 
    to the framework, allocating resources to task requests, and maintaining 
    the associated bookkeeping.
    """
    # RM init
    def __init__(self, fwk):
        """
        declaration of bookkeeping values
        """
        self.rm_start_of_time = time.time()
        # ref to framework
        self.fwk = fwk
        self.EM = None
        self.DM = None
        self.TM = None
        self.CM = None

        self.accurateNodes = False

        # bookkeeping for allocationa and accounting
        self.nodes = {}
        self.num_nodes = 0
        self.avail_nodes = list()
        self.alloc_nodes = list()
        self.total_cores = 0
        self.alloc_cores = 0
        self.avail_cores = 0
        self.processes = 0
        self.active_tasks = {} # tid:(owner, cores, procs)
        
        # hardware node topology
        self.cores_per_node = 1
        self.sockets_per_node = 1
        self.cores_per_socket = 1

        # other stuff
        self.max_ppn = 1   # the ppn for the whole submission (max ppn allowed by *software*)
        self.ppn = 1  # platform config ppn for the whole IPS
        self.myTopic = None
        self.service_methods = ['get_allocation', 'release_allocation']
        
        self.fwk.register_service_handler(self.service_methods,
                                  getattr(self,'process_service_request'))
    # RM initialize
    def initialize(self, dataMngr, taskMngr, configMngr, ftb, 
                   cmd_nodes=0, cmd_ppn=0):
        """
        Initialize resource management structures, references to other 
        managers (*dataMngr*, *taskMngr*, *configMngr*), and feature settings 
        (*ftb*).

        Resource information comes from the following in order of priority:

          * command line specification (*cmd_nodes*, *cmd_ppn*)
          * detection using parameters from platform config file
          * manual settings from platform config file

        The second two sources are obtained through 
        :py:meth:`resourceHelper.getResourceList`.
        """
        self.EM = eventManager(self)
        self.DM = dataMngr
        self.TM = taskMngr
        self.CM = configMngr
        self.FTB = ftb
        self.node_alloc_mode = self.CM.get_platform_parameter('NODE_ALLOCATION_MODE')

        print 'have not opened the file'
        time.sleep(100)
        rfile_name = os.path.join(self.CM.sim_map[self.CM.fwk_sim_name].sim_root, "resource_usage")
        self.reporting_file = open(rfile_name, "w")

        #-------------------------------
        # check cmd line resource spec
        #-------------------------------
        if cmd_nodes != 0 and cmd_ppn != 0:
            # use cmd resource specification
            self.host = "override_%s" % os.environ['HOST'] 
            self.max_ppn = cmd_ppn
            self.cores_per_node = cmd_ppn
            self.ppn = cmd_ppn
            self.sockets_per_node = 1
            self.accurateNodes = False
            listOfNodes = []
            for i in range(cmd_nodes):
                listOfNodes.append(("dummy_node%d" % i, cmd_ppn))
        else:
            self.ppn = 0
            #-------------------------------
            # get resource information
            #-------------------------------
            self.host = self.CM.get_platform_parameter('HOST')
            self.fwk.debug( 'RM: Host = %s', self.host)
            try:
                listOfNodes, self.cores_per_node, self.sockets_per_node,  \
                    self.max_ppn, self.accurateNodes = \
                    getResourceList(self.CM, self.host, self.FTB)
                #print "SSSSSSSSSSSSSSSSSS", self.cores_per_node, self.sockets_per_node, self.max_ppn
                self.fwk.warning('RM: listOfNodes = %s', str(listOfNodes))
                self.fwk.warning('RM: max_ppn = %d ', int(self.max_ppn))
            except Exception, e:
                print "can't get resource info"
                raise
        
            #-------------------------------
            # set ppn
            #-------------------------------
            uppn_config = self.CM.get_platform_parameter('PROCS_PER_NODE')
            if uppn_config == 0:
                user_ppn = self.max_ppn
            else:
                user_ppn = uppn_config
                self.fwk.debug("user set procs per node: %d", user_ppn)
                
            if user_ppn <= self.max_ppn:
                self.ppn = user_ppn
            else:
                self.fwk.warning("Platform specified  PROCS_PER_NODE is greater than batch job specification.")
                self.fwk.warning("Will use batch job specification to launch tasks")
                self.ppn = self.max_ppn

            #-----------------------------------
            # set cores/sockets per socket/node
            #-----------------------------------
            #print ">>>> CPN %d --- SPN %d" % (self.cores_per_node, self.sockets_per_node)
            if (self.cores_per_node % self.sockets_per_node) == 0: 
                self.cores_per_socket = self.cores_per_node / self.sockets_per_node
            else:
                self.fwk.warning("cpn (%d) not divisible by spn(%d) - setting spn to 1" % (self.cores_per_node, self.sockets_per_node))
                self.sockets_per_node = 1
                self.cores_per_socket = self.cores_per_node
        
        #-------------------------------
        # populate nodes
        #-------------------------------
        self.fwk.warning('RM: %d nodes and %d processors per node' % (len(listOfNodes), self.ppn))
        self.total_cores = self.add_nodes(listOfNodes)
        self.avail_cores = self.total_cores
        self.begin_RM_report()
        if self.FTB:
            #self.EM.publish('FTBEvents', 'RM reporting nodes', listOfNodes)  <-- Not needed anymore
            self.EM.subscribe('_IPS_NODE_STATUS', self.process_FTB_events)
            self.effected_task_list = []
        #self.printRMState()

    def process_service_request(self, msg):
        pass

    def begin_RM_report(self):
        """
        Print header information for resource usage reporting file.
        """
        print >> self.reporting_file, "# host:", self.host
        print >> self.reporting_file, "# total nodes:", self.num_nodes
        print >> self.reporting_file, "# processors per node:", self.ppn
        print >> self.reporting_file, "# time (in seconds since the | available | allocated | percent allocated | processes | percent used | notes "
        print >> self.reporting_file, "#   resource manager started |           |           |                   |           |              |"
        print >> self.reporting_file, "#-----------------------------------------------------------------------------------------------------------"
        self.report_RM_status('initial state of resources')

    def report_RM_status(self, notes = ""):
        """
        Print current RM status to the reporting_file ("resource_usage")
        Entries consist of:
         - time in seconds since beginning of time (__init__ of RM)
         - # cores that are available
         - # cores that are allocated
         - % allocated cores
         - # processes launched by task
         - % cores used by processes
         - notes (a description of the event that changed the resource usage)
        """
        print >> self.reporting_file, " %27.5f |" % (time.time() - self.rm_start_of_time),
        print >> self.reporting_file, " %8d |" % self.avail_cores,
        print >> self.reporting_file, " %8d |" % self.alloc_cores,
        print >> self.reporting_file, " %16.2f |" % (100 * (float(self.alloc_cores) / self.total_cores)),
        print >> self.reporting_file, " %8d |" % self.processes,
        print >> self.reporting_file, " %10.2f  # " % (100 * (float(self.processes) / self.total_cores)),
        print >> self.reporting_file,  notes
        self.reporting_file.flush()

    def printRMState(self):
        """
        Print the node tree to ``stdout``.
        """
        print "*** RM.nodeTable ***"
        for n,i in self.nodes.items():
            print n
            i.print_sockets()
        print "====================="

    def add_nodes(self, listOfNodes):
        """
        Add node entries to ``self.nodes``.  Typically used by 
        :py:meth:`.initialize` to initialize ``self.nodes``.
        May be used to add nodes to a dynamic allocation in the future.

        *listOfNodes* is a list of tuples (*node name*, *cores*).  
        ``self.nodes`` is a dictionary where the keys are the *node names* and 
        the values are :py:class:`node_structure.Node` structures.

        Return total number of cores.
        """
        tot_cores = 0
        for n, p in listOfNodes:
            if n not in self.nodes:
                self.nodes.update({n:Node(n, self.sockets_per_node, 
                                          self.cores_per_node, p)})
                self.num_nodes += 1
                self.avail_nodes.append(n)
                tot_cores += p
        """ 
        ### AGS: SC09 demo code, also useful for debugging FT capabilities. 
        if self.FTB and not self.accurateNodes:
            self.resource_visualizer()
            print ">>> Nodes allocated."
            sys.stdout.flush()
        """
        return tot_cores

    # RM getAllocation
    def get_allocation(self, comp_id, nproc, task_id,
                       whole_nodes, whole_socks, task_ppn=0):
        """
        Traverse available nodes to return:

        If *whole_nodes* is ``True``:

          * *shared_nodes*: ``False``
          * *nodes*: list of node names
          * *ppn*: processes per node for launching the task
          * *max_ppn*: processes that can be launched
          * *accurateNodes*: ``True`` if *nodes* uses the actual names of the nodes, ``False`` otherwise.
        
        If *whole_nodes* is ``False``:

          * *shared_nodes*: ``True``
          * *nodes*: list of node names
          * *node_file_entries*: list of (node, corelist) tuples, where *corelist* is a list of core names.  Core names are integers from 0 to n-1 where n is the number of cores on a node.
          * *ppn*: processes per node for launching the task
          * *max_ppn*: processes that can be launched
          * *accurateNodes*: ``True`` if *nodes* uses the actual names of the nodes, ``False`` otherwise.

        Aguments:

          * *nproc*: the number of requested processes (int)
          * *comp_id*: component identifier, must be unique with respect to the framework (string)
          * *task_id*: task identifier from TM (int)
          * *method*: name of method (string)
          * *task_ppn*: ppn for this task (optional) (int)
        """
        if self.FTB:
            # check the FTB for new information
            self.EM.process_events()
        # get the component requirements for all of the components

        # set ppn for this task
        if task_ppn > 0:
            if task_ppn > self.ppn:
                if task_ppn > self.max_ppn:
                    self.fwk.warning("task ppn exceeds machine ppn, using machine ppn instead")
                    ppn = self.max_ppn
                else:
                    ppn = task_ppn
            else:
                ppn = task_ppn
        else:
            ppn = self.ppn

        if (nproc < ppn):
            ppn = nproc

        # check if partial node allocation is possible
        if self.node_alloc_mode == "EXCLUSIVE":
            if not (whole_nodes and whole_socks):
                self.fwk.warning("No partial node allocation available on this platform, using whole nodes instead.")
            whole_nodes = True
            whole_socks = True
        if len(self.nodes) == 1:
            if whole_nodes or whole_socks:
                self.fwk.warning("No whole node or socket allocation available on this platform, sharing nodes instead.")
            whole_nodes = False
            whole_socks = False

        # Are there enough cores to satisfy the request?
        # Returns the list of nodes that fit the bill
        allocation_possible = False
        if whole_nodes:
            allocation_possible, nodes = self.check_whole_node_cap(nproc, ppn)
        elif whole_socks:
            allocation_possible, nodes = self.check_whole_sock_cap(nproc, ppn)
        else:
            allocation_possible, nodes = self.check_core_cap(nproc, ppn)

        if not allocation_possible:
            if nodes == "bad":
                c = ceil(float(nproc)/ppn)
                raise BadResourceRequestException(comp_id, task_id, c, c - len(self.avail_nodes))
            if nodes == "mismatch":
                raise ResourceRequestMismatchException(comp_id, task_id,
                                                       nproc, ppn,
                                                       self.total_cores,
                                                       self.max_ppn)
            if nodes == "insufficient":
                c = ceil(float(nproc)/ppn)
                raise InsufficientResourcesException(comp_id, task_id, 
                                                 c, c - len(self.avail_nodes))
        else:
            try:
                self.processes += nproc
                k = 0
                alloc_procs = 0
                node_file_entries = []
                if whole_nodes:
                    #-------------------------------
                    # whole node allocation
                    #-------------------------------
                    for n in nodes:
                        procs, cores = self.nodes[n].allocate(whole_nodes,
                                                              whole_socks,
                                                              task_id, comp_id,
                                                              ppn)
                        self.avail_nodes.remove(n)
                        self.alloc_nodes.append(n)
                        node_file_entries.append((n, cores))
                        k += procs
                    self.alloc_cores += k
                    self.avail_cores -= k
                    self.active_tasks.update({task_id:(comp_id, nproc, k)})
                elif whole_socks:
                    #-------------------------------
                    # whole sock allocation
                    #-------------------------------
                    for n in nodes:
                        node = self.nodes[n]
                        if node.avail_cores > 0:
                            to_alloc = min([ppn, node.avail_cores,
                                           nproc - alloc_procs])
                            #print "&&&&& allocate task_id %d node %s %d cores" % (task_id, n, to_alloc)
                            procs, cores = node.allocate(whole_nodes,
                                                         whole_socks,
                                                         task_id, comp_id,
                                                         to_alloc)
                            k += len(cores)
                            alloc_procs = min([ppn, len(cores)])
                            node_file_entries.append((n, cores))
                            if n not in self.alloc_nodes:
                                self.alloc_nodes.append(n)
                                if node.avail_cores - node.total_cores == 0:
                                    self.avail_nodes.remove(n)

                    self.alloc_cores += k
                    self.avail_cores -= k
                    self.active_tasks.update({task_id:(comp_id, nproc, k)})
                else:
                    #-------------------------------
                    # single core allocation
                    #-------------------------------
                    for n in nodes:
                        node = self.nodes[n]
                        if node.avail_cores > 0:
                            to_alloc = min([ppn, node.avail_cores,
                                           nproc - k])
                            #print "&&&&& allocate task_id %d node %s %d cores" % (task_id, n, to_alloc)
                            procs, cores = node.allocate(whole_nodes,
                                                         whole_socks,
                                                         task_id, comp_id,
                                                         to_alloc)
                            k += procs
                            node_file_entries.append((n, cores))
                            if n not in self.alloc_nodes:
                                self.alloc_nodes.append(n)
                                if node.avail_cores - node.total_cores == 0:
                                    self.avail_nodes.remove(n)

                    self.alloc_cores += k
                    self.avail_cores -= k
                    self.active_tasks.update({task_id:(comp_id, nproc, k)})
            except:
                print "Available Nodes:"
                for nm in self.avail_nodes:
                    n = self.nodes[nm]
                    print n.name, n.avail_cores
                    n.print_sockets()
                print "\nAllocated Nodes:"
                for nm in self.alloc_nodes:
                    n = self.nodes[nm]
                    print n.name, n.avail_cores
                    n.print_sockets()
                print "\n ***** Neither List!"
                for nm, n in self.nodes.items():
                    if nm not in self.avail_nodes and nm not in self.alloc_nodes:
                        print nm, n.avail_cores
                        n.print_sockets()
                raise

            if whole_nodes:
                self.report_RM_status("allocation for task %d using whole nodes" % task_id)
                return not whole_nodes, nodes, ppn, self.max_ppn, self.accurateNodes
            else:
                self.report_RM_status("allocation for task %d using partial nodes" % task_id)
                return not whole_nodes, nodes, node_file_entries, ppn, self.max_ppn, self.accurateNodes

        """
        ### AGS: SC09 demo code, also useful for debugging FT capabilities.
        if self.FTB and not self.accurateNodes:
            self.resource_visualizer()
            task_name = self.map_task_owner(str(comp_id))
            if not task_name:
                task_name = task_id
            print ">>> Task", task_name, "running."
            sys.stdout.flush()
        """

    def check_whole_node_cap(self, nproc, ppn):
        """
        Determine if it is currently possible to allocate *nproc* processes 
        with a ppn of *ppn* and whole nodes.  Return ``True`` and list of 
        nodes to use if successful.  Return ``False`` and empty list if there 
        are not enough available resources at this time, but it is possible to 
        eventually satisfy the request.  Exception raised if the request can 
        never be fulfilled.
        """
        whole_cap = 0
        nodes = []
        try:
            for n in self.avail_nodes:
                node = self.nodes[n]
                if node.avail_cores == node.total_cores and node.avail_cores >= ppn:
                    whole_cap += ppn
                    nodes.append(n)
                    if whole_cap >= nproc:
                        return True, nodes
        except:
            self.fwk.exception("problem in RM.check_whole_node_cap")
            raise
        # check to see if it is possible to satify the request
        tot_cap = 0
        for n in self.nodes.values():
            tot_cap += min([ppn, n.total_cores])
            if tot_cap >= nproc:
                return False, "insufficient"
        
        if self.total_cores < nproc:
            return False, "bad"
        else:
            return False, "mismatch"

    def check_whole_sock_cap(self, nproc, ppn):
        """
        Determine if it is currently possible to allocate *nproc* processes 
        with a ppn of *ppn* and whole sockets.  Return ``True`` and list of 
        nodes to use if successful.  Return ``False`` and empty list if there 
        are not enough available resources at this time, but it is possible to 
        eventually satisfy the request.  Exception raised if the request can 
        never be fulfilled.
        """
        nodes = []
        k = 0
        try:
            for n in self.avail_nodes:
                node = self.nodes[n]
                sk = 0
                for sock in node.sockets:
                    if sock.total_cores == sock.avail_cores:
                        # whole socket
                        if n not in nodes:
                            nodes.append(n)
                        if sock.avail_cores > ppn:
                            sk += ppn
                        else:
                            sk += sock.avail_cores
                        if sk >= ppn:
                            break
                k += sk
                if k >= nproc:
                    return True, nodes
        except:
            self.fwk.exception("problem in RM.check_whole_sock_cap")
            raise
        # check to see if it is possible to satify the request
        tot_cap = 0
        for n in self.nodes.values():
            tot_cap += min([ppn, n.total_cores])
            if tot_cap >= nproc:
                return False, "insufficient"
        
        if self.total_cores < nproc:
            return False, "bad"
        else:
            return False, "mismatch"


    def check_core_cap(self, nproc, ppn):
        """
        Determine if it is currently possible to allocate *nproc* processes 
        with a ppn of *ppn* without further restrictions..  Return ``True`` 
        and list of nodes to use if successful.  Return ``False`` and empty 
        list if there are not enough available resources at this time, but it 
        is possible to eventually satisfy the request.  Exception raised if 
        the request can never be fulfilled.
        """
        #print "++++++++++++++++"
        nodes = []
        k = 0
        try:
            for n in self.avail_nodes:
                node = self.nodes[n]
                if nproc - k < ppn:
                    if node.avail_cores >= nproc - k:
                        k = nproc
                        nodes.append(n)
                        return True, nodes
                    else:
                        k += node.avail_cores
                        nodes.append(n)
                else:
                    if node.avail_cores >= ppn:
                        k += ppn
                        nodes.append(n)
                    else:
                        k += node.avail_cores
                        nodes.append(n)
                if k >= nproc:
                    return True, nodes
        except:
            self.fwk.exception("problem in RM.check_core_cap")
            raise
        # check to see if it is possible to satify the request
        tot_cap = 0
        for n in self.nodes.values():
            tot_cap += min([ppn, n.total_cores])
            if tot_cap >= nproc:
                return False, "insufficient"
        
        if self.total_cores < nproc:
            return False, "bad"
        else:
            return False, "mismatch"

    # RM releaseAllocation
    def release_allocation(self, task_id, status):
        """
        Set resources allocated to task *task_id* to available.  *status* is 
        not used, but may be used to correlate resource failures to task 
        failures and implement task relaunch strategies.
        """
        if self.FTB:
            self.EM.process_events()

        o, nproc, num_cores = self.active_tasks[task_id]
        tot_avc = 0
        for n, node in self.nodes.items():
            if task_id in node.task_ids:
                node.release(task_id, o)
                if node.avail_cores > 0 and n not in self.avail_nodes:
                    self.avail_nodes.append(n)
                if node.avail_cores == node.total_cores:
                    self.alloc_nodes.remove(n)
            tot_avc += node.avail_cores

        self.avail_cores += num_cores
        self.alloc_cores -= num_cores
        self.processes -= nproc
        
        self.report_RM_status('released nodes for task %d' % task_id)

        """
        ### AGS: SC09 demo code, also useful for debugging FT capabilities.
        if self.FTB and not self.accurateNodes:
            self.resource_visualizer()
            task_name = self.map_task_owner(str(owner))
            if not task_name:
                task_name = task_id
            if task_id in self.effected_task_list:
                print ">>> Task", task_name, "completed with errors."
            else:
                print ">>> Task", task_name, "completed without errors."
            sys.stdout.flush()
        """

        if self.FTB:
            if task_id in self.effected_task_list:
                self.effected_task_list.remove(task_id)
                raise AllocatedNodeDownException(str(down),task_id,owner)

        return True

    def process_FTB_events(self, topic, event):
        # messages are gotten and processed here
        # assuming all events are from the FTB
        try:
            b = event.getBody()
            self.fwk.debug("Processing FTB event: %s, %s", b['NODE_STATUS'], b['NODE_LIST'])

            for node in b['NODE_LIST']:

                """
                ### AGS: SC09 demo code, also useful for debugging FT capabilities. 
                if self.FTB and not self.accurateNodes:
                    node = int(node)
                """

                self.nodes[node].status = b['NODE_STATUS']

                if b['NODE_STATUS'] == 'NODE_DOWN':
                    if node in self.avail_nodes:
                        self.avail_nodes.remove(node)
                        self.nodes[node]['available'] = False
                    elif node in self.alloc_nodes:
                        if self.nodes[node]['task_id'] not in self.effected_task_list:
                            self.effected_task_list.append(self.nodes[node]['task_id'])
                elif b['NODE_STATUS'] == 'NODE_UP':
                    if (node not in self.avail_nodes) and (node not in self.alloc_nodes):
                        try:
                            self.avail_nodes.append(node)
                            self.nodes[node].is_available = 1
                        except:
                            self.add_nodes([node])
        except Exception, e:
            print e
            print ">>> Problems with the FTB."

    """
    ### AGS: SC09 demo code, also useful for debugging FT capabilities.
    def resource_visualizer(self):
        print time.strftime("\n\n\n%Y-%m-%d %H:%M:%S", time.localtime())
        print "-------------------"
        print "Resource Visualizer"
        print "-------------------"
        count = 0
        for n in sorted(self.nodes.keys()):
            i = self.nodes[n]
            if i['status'] == 'NODE_DOWN':
                #TODO: this is an old way of formatting print output, that will eventually be 
                #      removed from the language, hence switch to str.format().
                print "%4s" %'X',
            elif i['status'] == 'NODE_UP':
                if i['available'] == True:
                    print "%4s" %'.',
                elif n in self.alloc_nodes:
                    task_name = self.map_task_owner(str(i['owner']))
                    if not task_name:
                        task_name = i['task_id']
                    print "%4s" %task_name,
            count += 1
            if count%4 == 0:
                print "\n",
            sys.stdout.flush()
        print "-------------------"
        sys.stdout.flush()

    def map_task_owner(self, owner):
        if owner.find('medium_worker') >= 0:
            return 'A'
        elif owner.find('large_worker') >= 0:
            return 'B'
        elif owner.find('small_worker') >= 0:
            return 'C'
        else:
            return None
    """

    # RM SendEvent
    def sendEvent(self, eventName, info):
        """
        wrapper for constructing and publishing EM events
        """
        # -------------------------------
        #     send an event
        # -------------------------------
        # populate event body
        eventBody = {}
        eventBody.update({'event name':eventName, 'topic':'test', 'sender':'RM',
                          'data':'A resource event has occured'})
        eventBody.update(info)
        # send event on topic
        # self.myTopic.sendEvent(eventName, eventBody)


#myRM = resourceManager()
#myRM.initialize()
