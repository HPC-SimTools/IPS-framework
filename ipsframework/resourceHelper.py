"""
The Resource Helper file contains all of the code needed to figure out what
host we are on and what resources we have.  Taking this out
of the resource manager will allow us to test it independent
of the IPS.
"""

import os
import subprocess
from math import ceil
from .ipsExceptions import InvalidResourceSettingsException


def get_qstat_jobinfo():
    """
    Use ``qstat -f $PBS_JOBID`` to get the number of nodes and ppn of the
    allocation.  Typically works on PBS systems.
    """
    try:
        job_id = os.environ['PBS_JOBID']
    except Exception:
        raise

    shell_host = None
    try:
        shell_host = os.environ['HOST']
    except Exception:
        pass

    command = 'qstat -f %s' % (job_id)
    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        out = p.stdout.readlines()
        if shell_host == 'stix':
            start_line = -1
            end_line = -1
            ppn = 0
            for i, line in enumerate(out):
                if line.strip().startswith('exec_host ='):
                    start_line = i
                if start_line != -1 and end_line == -1:
                    if '=' in line:
                        end_line = i
                if line.strip().startswith('Resource_List.nodes = '):
                    if 'ppn=' in line:
                        ppn = int(line.split('=')[-1])
                    else:
                        ppn = 8

            host_out = ''
            for i in range(start_line, end_line + 1):
                host_out += out[i]

            host_string = host_out.strip().replace(' \n', '').split('=')[1]
            node_list = [t .strip() for t in host_string.split('+')]
            num_nodes = len(node_list)
            return num_nodes, ppn, True, node_list
        else:
            width = [x.strip() for x in out if 'Resource_List.mppwidth' in x]
            mpp_npp = [x.strip() for x in out if 'Resource_List.mppnppn' in x]
            num_procs = int(width[0].split('=')[1])
            if len(mpp_npp) > 0:
                ppn = int(mpp_npp[0].split('=')[1])
            num_nodes = int(ceil(float(num_procs) / float(ppn)))
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
    except Exception:
        raise

    command = 'qstat -f %s' % (job_id)
    p = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    p.wait()
    if p.returncode == 0:
        out = p.stdout.readlines()
        found_start = False
        found_end = False
        lines = ''
        for line in out:
            if 'exec_host' in line:
                found_start = True
                lines += line.strip()
            elif 'Hold_Types' in line:
                found_end = True
            elif found_start and not found_end:
                lines += line.strip()

        lines = lines.split('=')[1].strip()
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
        ppn = max([len(p[1]) for p in ndata])
        return len(ndata), ppn, False, ndata
    else:
        raise Exception('Error in call to qstat')


def get_checkjob_info():
    ndata = []
    nodes = []
    cmd = "checkjob $PBS_JOBID"
    p = 0
    tot_procs = 0
    data_lines = []
    job_id = os.getenv('PBS_JOBID', '')
    mixed_nodes = False
    # Test for interactive use on batch platforms
    if job_id == '':
        raise Exception('Cannot find PBS_JOBID')
    # run checkjob $PBS_JOBID
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        lines = [line.strip() for line in proc.stdout.readlines()]
        start = end = 0
        for k, line in enumerate(lines):
            x = line.rstrip()
            if x == "Allocated Nodes:" and start == 0:
                start = k + 1
            elif x == '' and start > 0 and end == 0:
                end = k
            if x.find("Total Requested Tasks:") > -1:
                _, b = x.split(":")
                b = b.strip()
                tot_procs = int(b)
        for line in lines[start:end + 1]:
            if line.strip() != "":
                data_lines.append(line.strip())
    except Exception as e:
        print(e)
        raise e
        # return nodes, procs
    # parse output to get allocated nodes data
    """
    There are two different formats for listing nodes that the job has access to.
    For the small numbers of nodes:
            [node_id:tasks_per_node]+

    For large numbers of nodes:
            [list of comma separated node_ids and node_id ranges]*tasks_per_node
    """
    if data_lines[0].find(":") > -1:
        # small node number format
        try:
            for j in data_lines:
                j = j[1:len(j) - 1]  # strip off first [ and last ]
                pairs = j.split('][')
                for i in pairs:
                    ndata.append(i.split(':'))
            # parse allocated nodes data [nid:nprocs]...
            for (m, p) in ndata:
                nodes.append(m)
        except Exception as e:
            print('problem parsing - small format')
            raise e
    elif data_lines[0].find("*") > -1:
        # large node number format
        try:
            nodes_str = ""
            data = ""
            # put the whole thing on one line
            data = "".join(data_lines)
            nodes_str, p = data.split("*")
            nodes_str = nodes_str.strip("[]")
            ranges = nodes_str.split(",")
            for r in ranges:
                if r.find("-") > -1:
                    # this is a range
                    ss, es = r.split("-")
                    s = int(ss)
                    e = int(es)
                    for i in range(s, e + 1):
                        nodes.append(str(i))
                else:
                    # this is a single node id
                    nodes.append(r)
            ndata = [(n, p) for n in nodes]
        except Exception as e:
            print('problem parsing - large format')
            raise e
    else:
        # TODO: make this into a real exception type
        raise Exception("could not parse resource data")
    if abs(len(nodes) * int(p) - tot_procs) > 1:
        print('len(nodes) = %d  p = %d  tot_procs = %d' % (len(nodes), int(p), tot_procs))
        print("something wrong with parsing - node count*cores does not match task count")
        raise Exception("something wrong with parsing - node count*cores does not match task count")
    return nodes, int(p), mixed_nodes, ndata


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
    except Exception:
        raise
    try:
        ppn = os.environ['SLURM_TASKS_PER_NODE']
        ppn = int(ppn.split("(")[0])
    except Exception:
        try:
            ppn = os.environ['SLURM_JOB_TASKS_PER_NODE']
            ppn = int(ppn.split("(")[0])
        except Exception:
            raise
    max_p = ppn
    try:
        nproc = int(os.environ['SLURM_NPROC'])
    except Exception:
        # need to set later
        nproc = 0

    try:
        cmd = 'scontrol show hostname %s' % nodelist
        sys_nodes = subprocess.check_output(cmd.split(), encoding='UTF-8').strip().split('\n')
        nodes.extend([(k, ppn) for k in sys_nodes])
        print('IPS SLURM_NODES = ', nodes)
    except Exception:
        raise

    if 0 < nproc < len(nodes) * max_p:
        mixed_nodes = True
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
        core_list = core_list_all
        node_dict = {}
        for core in core_list:
            # core is really a node name
            try:
                node_dict[core] += 1
            except KeyError:
                node_dict[core] = 1
        listOfNodes = list(node_dict.items())
        max_p = max(node_dict.values())
        mixed_nodes = (max_p != min(node_dict.values()))
        return len(listOfNodes), max_p, mixed_nodes, listOfNodes
    except Exception:
        try:
            node_count = int(os.environ['PBS_NNODES'])
            return node_count, 0, False, []
        except Exception:
            raise


def manual_detection(services):
    """
    Use values listed in platform configuration file.
    """
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
        n = listOfNodes[-1][0]
        listOfNodes[-1] = (n, tot_procs % ppn)
    return num_nodes, ppn, False, listOfNodes


def getResourceList(services, host, partial_nodes=False):
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
        print("=======================================================")
        print(num_nodes, ppn, mixed_nodes, listOfNodes)
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
            for n in range(num_nodes):
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
        print("WARNING: no node detection strategy specified in platform config file ('NODE_DETECTION'). "
              "Valid options are: checkjob, qstat, pbs_env, slurm_env, manual.  Trying all detection schemes.")
        try:
            num_nodes, ppn, mixed_nodes, listOfNodes = get_checkjob_info()
            accurateNodes = True
        except Exception:
            try:
                num_nodes, ppn, mixed_nodes, listOfNodes = get_qstat_jobinfo()
                accurateNodes = False
            except Exception:
                try:
                    num_nodes, ppn, mixed_nodes, listOfNodes = get_pbs_info()
                    if ppn == 0:
                        ppn = 1
                    if not listOfNodes:
                        for n in range(num_nodes):
                            listOfNodes.append(("dummynode%d" % n, ppn))
                    else:
                        accurateNodes = True
                except Exception:
                    try:
                        num_nodes, ppn, mixed_nodes, listOfNodes = get_slurm_info()
                        accurateNodes = True
                    except Exception:
                        try:
                            num_nodes, ppn, mixed_nodes, listOfNodes = manual_detection(services)
                            accurateNodes = False
                        except Exception:
                            print("*** NO DETECTION MECHANISM WORKS ***")
                            raise
    # detect topology
    cpn = int(services.get_platform_parameter('CORES_PER_NODE'))
    spn = int(services.get_platform_parameter('SOCKETS_PER_NODE'))
    if cpn <= 0:
        cpn = ppn
    elif cpn < ppn:
        ppn = cpn
        if not mixed_nodes:
            for i, node in enumerate(listOfNodes):
                name = node[0]
                listOfNodes[i] = (name, ppn)
    if spn <= 0:
        spn = 1
    elif spn > cpn:
        raise InvalidResourceSettingsException("spn > cpn", spn, cpn)
    elif cpn % spn != 0:
        raise InvalidResourceSettingsException("spn not divisible by cpn", spn, cpn)
    return listOfNodes, cpn, spn, ppn, accurateNodes
