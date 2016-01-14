"""
The Resource Helper file contains all of the code needed to figure out what
host we are on and what resources we have.  Taking this out
of the resource manager will allow us to test it independent
of the IPS.
"""

import sys
import os
import shutil
import subprocess
from math import ceil
from ipsExceptions import InvalidResourceSettingsException

def get_qstat_jobinfo():
    """
    Use ``qstat -f $PBS_JOBID`` to get the number of nodes and ppn of the 
    allocation.  Typically works on PBS systems.
    """
    try:
        job_id = os.environ['PBS_JOBID']
    except:
        raise
    
    shell_host=None
    try:
        shell_host = os.environ['HOST']
    except:
        pass
    

    command = 'qstat -f %s' % (job_id)
    p = subprocess.Popen(command.split(),stdout=subprocess.PIPE)
    p.wait()
    if (p.returncode == 0):
        out = p.stdout.readlines()
        if shell_host == 'stix':
            start_line = -1
            end_line = -1
            ppn = 0
            for i in range(len(out)):
                line = out[i]
                if line.strip().startswith('exec_host ='):
                    start_line = i
                if start_line != -1 and end_line == -1:
                    if ('=' in line):
                        end_line = i
                if line.strip().startswith('Resource_List.nodes = '):
                    if ('ppn=') in line:
                        ppn = int(line.split('=')[-1])
                    else:
                        ppn = 8
            
            host_out = ''
            for i in range(start_line, end_line+1):
                host_out += out[i]
            
            host_string = host_out.strip().replace(' \n', '').split('=')[1]
            node_list = [t .strip() for t in host_string.split('+')]
            num_nodes = len(node_list)
            return num_nodes, ppn, True, node_list
        else:
            width = [l.strip() for l in out if 'Resource_List.mppwidth' in l]
            mpp_npp = [l.strip() for l in out if 'Resource_List.mppnppn' in l]    
            num_procs  = int(width[0].split('=')[1])
            if len(mpp_npp) > 0:
                ppn = int(mpp_npp[0].split('=')[1])
            num_nodes = int(ceil(float(num_procs)/float(ppn)))
            return num_nodes, ppn, False, []
    else:
        raise Exception('Error in call to qstat.')

def get_qstat_jobinfo2():
    """
    A second way to use ``qstat -f $PBS_JOBID`` to get the number
    of nodes and ppn of the 
    allocation.  Typically works on PBS systems.
    """
    try:
        job_id = os.environ['PBS_JOBID']
    except:
        raise

    command = 'qstat -f %s' % (job_id)
    p = subprocess.Popen(command.split(),stdout=subprocess.PIPE)
    p.wait()
    if (p.returncode == 0):
        out = p.stdout.readlines()
        found_start = False
        found_end = False
        lines = ''
        for l in out:
            if 'exec_host' in l:
                found_start = True
                lines += l.strip()
            elif 'Hold_Types' in l:
                found_end = True
            elif found_start and not found_end:
                lines += l.strip()

        #print lines
        lines = lines.split('=')[1].strip()
        #print lines
        ppn = 1
        nodes = []
        ndata = []
        for k in lines.split('+'):
            node_name, procid = k.split('/')
            if node_name not in nodes:
                nodes.append(node_name)
                ndata.append((node_name, [procid]))
            else:
                i = nodes.index(node_name)
                ndata[i][1].append(procid)
        #print ndata
        ppn = max([len(p[1]) for p in ndata])
        #width = [l.strip() for l in out if 'Resource_List.mppwidth' in l]
        #mpp_npp = [l.strip() for l in out if 'Resource_List.mppnppn' in l]    
        #num_procs  = int(width[0].split('=')[1])
        #if len(mpp_npp) > 0:
        #    ppn = int(mpp_npp[0].split('=')[1])
        #num_nodes = int(ceil(float(num_procs)/float(ppn)))
        #return num_nodes, ppn, False, []
        return len(ndata), ppn, False, ndata
    else:
        raise Exception('Error in call to qstat')

def get_checkjob_info():
    ndata = []
    procs = 0
    nodes = []
    cmd = "checkjob $PBS_JOBID"
    p = 0
    tot_procs = 0
    data_lines = []
    job_id = os.getenv('PBS_JOBID', '')
    mixed_nodes = False
    # Test for interactive use on batch platforms
    if (job_id == ''):
            return [1], 1
    # run checkjob $PBS_JOBID
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        lines = [l.strip () for l in proc.stdout.readlines()]
        #print '============== lines ======================'
        #for l in lines : print l
        #print '============== lines ======================'
        start = end = 0
        for k in range(len(lines)):
            x = lines[k].rstrip()
            #print x
            if x == "Allocated Nodes:" and start == 0:
                start = k + 1
                #print ' start = ', start
            elif x == '' and start > 0 and end == 0:
                end = k
                #print ' end = ', end
                #print lines[start:end]	
            if x.find("Total Requested Tasks:") > -1:
                a,b = x.split(":")
                b = b.strip()
                tot_procs = int(b) 
        #print "total procs", tot_procs
        for line in lines[start:end+1]:
            #print '@@@@@@@', line
            if line.strip() != "":
                data_lines.append(line.strip())
        #print '%%%%%%%%%%%%%%%%', data_lines
    except Exception, e:
        print e
        raise e
        #return nodes, procs
    # parse output to get allocated nodes data
    """
    There are two different formats for listing nodes that the job has access to.
    For the small numbers of nodes:
            [node_id:tasks_per_node]+

    For large numbers of nodes:
            [list of comma separated node_ids and node_id ranges]*tasks_per_node
    """
    if data_lines[0].find(":") > -1:
        #print '------------ CASE 1'
        #small node number format
        try:
            for j in data_lines:
                #print j
                j = j[1:len(j)-1] # strip off first [ and last ]
                #print j
                pairs = j.split('][')
                #print pairs
                for i in pairs:
                    ndata.append(i.split(':'))
            # parse allocated nodes data [nid:nprocs]...
            for (m, p) in ndata:
                #m,p = n.split(':')
                nodes.append(m)
                #print '##############', nodes
        except Exception, e:
            print 'problem parsing - small format'
            raise e
    elif data_lines[0].find("*") > -1:
            #large node number format
        try:
            nodes_str = ""
            data = ""
            procs_str = ""
            #put the whole thing on one line
            data = "".join(data_lines)
            #print "one line: ", data
            nodes_str, p = data.split("*")
            #print "split the tasks_per_node: ", nodes_str
            nodes_str = nodes_str.strip("[]")
            #print "strip brackets: ", nodes_str
            ranges = nodes_str.split(",")
            #print "ranges: ", ranges
            for r in ranges:
                if r.find("-") > -1:
                    #this is a range
                    ss,es = r.split("-")
                    #print ss
                    #print es
                    s = int(ss)
                    e = int(es)
                    #print range(s,e)
                    for i in range(s,e+1):
                        nodes.append(str(i))
                else:
                    #this is a single node id
                    nodes.append(r)
            ndata = [(n, p) for n in nodes]              
        except Exception, e:
            print 'problem parsing - large format'
            raise e
    else:
            # TODO: make this into a real exception type
        raise "could not parse resource data"
    #print nodes, p, tot_procs
    if abs(len(nodes)*int(p) - tot_procs) > 1 :
        print 'len(nodes) = %d  p = %d  tot_procs = %d' % (len(nodes), int(p), tot_procs)
        print "something wrong with parsing - node count*cores does not match task count"
        raise Exception("something wrong with parsing - node count*cores does not match task count")
    print nodes, int(p), mixed_nodes, ndata
    return nodes, int(p), mixed_nodes, ndata
#    return nodes, int(p)


def get_checkjob_info_old():
    """
    Use ``checkjob $PBS_JOBID`` to get the node names and core counts of 
    allocation.  Typically works in a Cray environment.

    .. note:: Two formats for outputing resource information.  

               1. [node_id:tasks_per_node]+
               2. ([comma separated list of node_ids and node_id ranges]*tasks_per_node)+

    """
    ndata = []
    procs = 0
    cmd = "checkjob $PBS_JOBID"
    tot_procs = 0
    data_lines = []
    
    try:
        job_id = os.environ['PBS_JOBID']
    except:
        print 'problems getting job id'
        raise

    """
    try:
        hname = os.environ['HOST']
        if hname.find('.') > 0:
            hname = hname.split('.')[0]
        for k in range(len(hname)):
            if hname[k].isdigit():
                n = hname[:k]
                break
        print 'hostname prefix is %s' % n
        frmt_str = n + "%0" + str(len(hname[k:])) + "d"
    except:
        print 'problems getting hostname'
        raise
    """

    # run checkjob $PBS_JOBID
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        lines = proc.stdout.readlines()
        for k in range(len(lines)):
            x = lines[k].rstrip()
            if x.find("Allocated Nodes:") > -1:
                start = k + 1
            elif x.find("StartCount:") > -1:
                end = k
            if x.find("Total Requested Tasks:") > -1:
                a,b = x.split(":")
                b = b.strip()
                tot_procs = int(b)
        for line in lines[start:end]:
            if line.strip() != "":
                data_lines.append(line.strip())
    except:
        print 'problems getting checkjob output'
        raise

    """
    There are two different formats for listing nodes that the job has access to.
    For the small numbers of nodes:
        [node_id:tasks_per_node]+

    For large numbers of nodes:
        [list of comma separated node_ids and node_id ranges]*tasks_per_node(:[list of comma separated node_ids and node_id ranges]*tasks_per_node)*
    """
    data_lines = "".join(data_lines)
    mixed_nodes = False
    max_p = 0
    #print data_lines
    # large node numbers mode
    try:
        if data_lines.find("*") > -1:
            # split by :
            data_lines = data_lines.split(":")
            for d in data_lines:
                nids, ppn = d.split("*")
                ppn = int(ppn)
                if max_p < ppn:
                    if max_p > 0:
                        mixed_nodes = True                        
                    max_p = ppn
                nids = nids.strip("[]")
                ranges = nids.split(",")
                for be in ranges:
                    try:
                        b, e = be.split("-")
                        #ndata.extend([(frmt_str % k, ppn) for k in range(int(b), int(e) + 1)])
                        ndata.extend([(str(k), ppn) for k in range(int(b), int(e) + 1)])
                    except:
                        #ndata.append((frmt_str % int(be), ppn))
                        ndata.append((be, ppn))
        else:
            #small node number format
            data_lines = data_lines.strip('[]')
            pairs = data_lines.split("][")
            #print "pairs", pairs
            for i in pairs:
                #print i
                m, p = i.split(":")
                p = int(p)
                if max_p < p:
                    if max_p > 0:
                        mixed_nodes = True                        
                    max_p = p
                #ndata.append((frmt_str % int(m), p))
                ndata.append((m, p))
    except:
        raise

    nodes = len(ndata)
    return nodes, max_p, mixed_nodes, ndata

def get_slurm_info():
    """
    Access environment variables set by Slurm to get the node names, 
    tasks per node and number of processes.

      ``SLURM_NODELIST``
      ``SLURM_TASKS_PER_NODE`` or ``SLURM_JOB_TASKS_PER_NODE``
      ``SLURM_NPROC``
    """
    nodes = []
    mixed_nodes = False
    try:
        nodelist = os.environ['SLURM_NODELIST']
    except:
        raise
    try:
        ppn = os.environ['SLURM_TASKS_PER_NODE']
        ppn = int(ppn.split("(")[0])
    except:
        try:
            ppn = os.environ['SLURM_JOB_TASKS_PER_NODE']
            ppn = int(ppn.split("(")[0])
        except:
            #print "can't find ppn"
            raise
    max_p = ppn
    try:
        nproc = int(os.environ['SLURM_NPROC'])
    except:
        # need to set later
        nproc = 0
    try:
        # parse node list for node names
        if nodelist.find('[') > -1:
            # there is more than one node, need to parse list
            n, r = nodelist.split('[')
            #print l
            r = r.strip(']')
            ranges = r.split(",")
            for r in ranges:
                if '-' in r:
                    b, e = r.split("-")
                    frmt_str = n + "%0" + str(len(e)) + "d"                    
                else:
                    b, e = r, None
                    frmt_str = n + "%0" + str(len(b)) + "d"
                if e:
                    nodes.extend([(frmt_str % k, ppn) for k in range(int(b), int(e) + 1)])
                else:
                    nodes.append((frmt_str % int(b), ppn))

        elif nodelist.find(',') > -1:
            nodes.extend([(k, ppn) for k in nodelist.split(',')])
        else:
            nodes.append((nodelist, ppn))
            
    except:
        # print "problems parsing slurm_nodelist"
        raise

    if nproc > 0 and nproc < len(nodes) * max_p:
        mixed_nodes = True
        #print nproc
        #print max_p
        #print nodes[-1][1]
        nodes[-1][1] = nproc % max_p

    return len(nodes), max_p, mixed_nodes, nodes 

def get_pbs_info():
    """
    Access info about allocation from PBS environment variables:

        ``PBS_NNODES``
        ``PBS_NODEFILE``
    """
    try:
        node_file = os.environ['PBS_NODEFILE']
        # core_list is a misnomer, it is a list of (repeated) node names
        # where the node names are repeated for each process they can service
        core_list_all = [line.strip() for line in open(node_file, 'r').readlines()]
        #core_list = [c for c in core_list_all if c != core_list_all[0]]
        core_list = core_list_all
        node_dict = {}
        for core in core_list:
            # core is really a node name
            try:
                node_dict[core] += 1
            except KeyError:
                node_dict[core] = 1
        listOfNodes = [(k,v) for k,v in node_dict.items()]
        max_p = max(node_dict.values())
        mixed_nodes = (max_p != min(node_dict.values()))
        accurateNodes = True
        return len(listOfNodes), max_p, mixed_nodes, listOfNodes
    except:
        try:
            node_count = int(os.environ['PBS_NNODES'])
            return node_count, 0, False, []
        except:
            raise

def manual_detection(services):
    """
    Use values listed in platform configuration file.
    """
    mixed_nodes = False
    listOfNodes = []
    num_nodes = int(services.get_platform_parameter('NODES'))
    ppn = int(services.get_platform_parameter('PROCS_PER_NODE'))
    tot_procs = int(services.get_platform_parameter('TOTAL_PROCS'))
    cpn = int(services.get_platform_parameter('CORES_PER_NODE'))
    if tot_procs == 0:
        if num_nodes == 0:
            if ppn == 0:
                if cpn == 0:
                    cpn = 1
                ppn = cpn
            num_nodes = 1
        tot_procs = num_nodes * ppn
                        
    for n in range(num_nodes):
        listOfNodes.append(("dummynode%d" % n, ppn))
    if tot_procs < num_nodes * (ppn - 1):
        #raise InvalidResourceSettingsException("total procs and nodes mismatch", tot_procs, num_nodes)
        mixed_nodes = True
        n = listOfNodes[-1][0]
        listOfNodes[-1] = (n, tot_procs % ppn)
    return num_nodes, ppn, False, listOfNodes


def get_topo(services):
    """
    Uses `hwloc <http://www.open-mpi.org/projects/hwloc/>`_ library calls in C 
    program ``topo_disco`` to detect the topology of a node in the allocation.
    Return the number of sockets and the number of cores.

    .. note:: Not available on all platforms.
    """
    print "***in get_topo"
    # TODO: change launch_str to use mpirun and command line flags from 
    # platform config.
    script = services.get_platform_parameter('HWLOC_DETECT_SCRIPT')
    print script
    launch_str = 'mpirun -n 1 -bind-to-core %s' % script
    p = subprocess.Popen(launch_str, shell=True, 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.STDOUT)
    p.wait()
    if p.returncode == 0:
        topo = p.communicate()[0]
        print topo
        return topo.count('Socket'), topo.count('Core')
    else:
        print "returncode = %d\nproblem launching: '%s'" % (p.returncode, launch_str)
        print topo

def getResourceList(services, host, ftb, partial_nodes=False):
    """
    Using the host information, the resources are detected.  Return list of 
    (<node name>, <processes per node>), cores per node, sockets per node, 
    processes per node, and ``True`` if the node names are accurate, ``False`` 
    otherwise.
    """
    listOfNodes = []
    # get the number of nodes for that machine
    num_nodes = 1
    ppn = 1
    spn = 1
    cpn = 1
    accurateNodes = False
    mixed_nodes = False

    node_detect_str = services.get_platform_parameter('NODE_DETECTION',
                                                      silent=True)
    if node_detect_str == "checkjob":
        num_nodes, ppn, mixed_nodes, listOfNodes = get_checkjob_info()
        print "======================================================="
        print num_nodes, ppn, mixed_nodes, listOfNodes
        accurateNodes = False
    elif node_detect_str == "qstat":
        num_nodes, ppn, mixed_nodes, listOfNodes = get_qstat_jobinfo()
        accurateNodes = False
    elif node_detect_str == "qstat2":
        num_nodes, ppn, mixed_nodes, listOfNodes = get_qstat_jobinfo2()
        accurateNodes = True
    elif node_detect_str == "pbs_env":
        num_nodes, ppn, mixed_nodes, listOfNodes = get_pbs_info()
        if ppn == 0:
            ppn = 1
        if not listOfNodes:
            for n in num_nodes:
                listOfNodes.append(("dummynode%d" % n, ppn))
        else:
            accurateNodes = True
    elif node_detect_str == "slurm_env":
        num_nodes, ppn, mixed_nodes, listOfNodes = get_slurm_info()
        accurateNodes = True
    elif node_detect_str == "manual":
        num_nodes, ppn, mixed_nodes, listOfNodes = manual_detection(services)
        accurateNodes = False
    else:
        print "WARNING: no node detection strategy specified in platform config file ('NODE_DETECTION').  Valid options are: checkjob, qstat, pbs_env, slurm_env, manual.  Trying all detection schemes."
        try:
            num_nodes, ppn, mixed_nodes, listOfNodes = get_checkjob_info()
            accurateNodes = True
        except:
            try:
                num_nodes, ppn, mixed_nodes, listOfNodes = get_qstat_jobinfo()
                accurateNodes = False
            except:
                try:
                    num_nodes, ppn, mixed_nodes, listOfNodes = get_pbs_info()
                    if ppn == 0:
                        ppn = 1
                    if not listOfNodes:
                        for n in num_nodes:
                            listOfNodes.append(("dummynode%d" % n, ppn))
                    else:
                        accurateNodes = True
                except:
                    try:
                        num_nodes, ppn, mixed_nodes, listOfNodes = get_slurm_info()
                        accurateNodes = True
                    except:
                        try:
                            num_nodes, ppn, mixed_nodes, listOfNodes = manual_detection()
                            accurateNodes = False
                        except:
                            print "*** NO DETECTION MECHANISM WORKS ***" 
                            raise
    # detect topology
    cpn = int(services.get_platform_parameter('CORES_PER_NODE'))
    spn = int(services.get_platform_parameter('SOCKETS_PER_NODE'))
    if cpn <= 0:
        cpn = ppn
    elif cpn < ppn:
        ppn = cpn
        if not mixed_nodes:
            for i in range(len(listOfNodes)):
                name = listOfNodes[i][0]
                listOfNodes[i] = (name, ppn)
    if spn <= 0:
        spn = 1
    elif spn > cpn:
        raise InvalidResourceSettingsException("spn > cpn", spn, cpn)
    elif cpn % spn != 0:
        raise InvalidResourceSettingsException("spn not divisible by cpn", spn, cpn)
    
        
    """
    ### AGS: SC09 demo code, also useful for debugging FT capabilities. 
    if not accurateNodes:
        for i in range(1, num_nodes+1):
            listOfNodes.append(i)

    if ftb:
        my_nids = open('my_nids', 'w')
        for i in range(len(listOfNodes)):
            my_nids.write(str(listOfNodes[i]) + '\n')
        my_nids.close()
    """
    #if cpn < ppn:
    #    cpn = ppn
    # return list of node names
    print listOfNodes, cpn, spn, ppn, accurateNodes
    return listOfNodes, cpn, spn, ppn, accurateNodes 


