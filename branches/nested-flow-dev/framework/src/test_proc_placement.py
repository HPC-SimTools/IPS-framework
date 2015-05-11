#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
"""
utility to help test resource parsing functions from resourceHelper

Notes:
  - These functions should not be dependent on anything from the framework.
  - Failed parsing will result in a message indicating the method does not work.
    You may want to turn on the exceptions and examine the output from the command
    to see if there was a change in how the output is presented, and thus problems
    parsing.

"""

from resourceHelper import get_checkjob_info, get_qstat_jobinfo, get_pbs_info, get_slurm_info, get_topo, get_qstat_jobinfo2
import subprocess
import os

def test_get_checkjob_info():
    try:
        print 'Testing get_checkjob_info:'
        n, ppn, mixed_nodes, lon = get_checkjob_info()
        print 'get_checkjob_info yields %d nodes and %d ppn' % (n, ppn)
        for name, p in lon:
            print '\t%s: %d' % (name, p)
    except:
        print 'get_checkjob_info does not work on this machine'
        raise

def test_get_qstat_jobinfo():
    try:
        print 'Testing get_qstat_jobinfo:'
        n, ppn, mixed_nodes, lon = get_qstat_jobinfo()
        print 'get_qstat_jobinfo yields %d nodes and %d ppn ' % (n, ppn)
        for name, p in lon:
            print '\t%s: %d' % (name, p)
    except:
        print 'get_qstat_jobinfo does not work on this machine'
        raise

def test_get_qstat_jobinfo2():
    try:
        print 'Testing get_qstat_jobinfo2:'
        n, ppn, mixed_nodes, lon = get_qstat_jobinfo2()
        print 'get_qstat_jobinfo2 yields %d nodes and %d ppn ' % (n, ppn)
        for name, l in lon:
            print '\t%s: ' % name, l
        return n, ppn, mixed_nodes, lon
    except:
        print 'get_qstat_jobinfo2 does not work on this machine'
        raise

def test_get_pbs_info():
    try:
        print 'Testing get_pbs_info:'
        nodes, ppn, mixed_nodes, lon = get_pbs_info()
        print 'get_pbs_info yields %d nodes and %d ppn ' % (nodes, ppn)
        for name, p in lon:
            print '\t%s: %d' % (name, p)

    except:
        print 'get_pbs_info does not work on this machine'
        raise

def test_get_slurm_info():
    try:
        print 'Testing get_slurm_info:'
        nodes, ppn, mixed_nodes, lon = get_slurm_info()
        print 'get_slurm_info yields %d nodes and %d ppn ' % (nodes, ppn)
        for name, p in lon:
            print '\t%s: %d' % (name, p)

    except:
        print 'get_slurm_info does not work on this machine'
        raise

def test_mpirun(nodes, ppn, mixed_nodes, lon):
    """
    tests the mpirun options provided under different implementations
     - mpt: MPI_DSM_CPULIST
     - mpt: hp_spec options ([host_list] [local_options] [-np] pcount prog [args]
     - openmpi: -H host_list, or --hostfile host_file
    """
    print "\n****\n"
    # get the version of mpirun (mpirun -v, mpirun --version)
    cmds = [['mpirun', '-v'],
            ['mpirun', '-V'],
            ['mpirun --version']]
    versions = []
    for c in cmds:
        try:
            process = subprocess.Popen(c, stdout=subprocess.PIPE, stderr = subprocess.STDOUT)
            process.wait()
            odata = process.communicate()[0]
            print odata
            #print odata.find('m')
            if odata.find('SGI') >= 0:
                versions.append('sgi')
            elif odata.find('Open MPI') >= 0:
                print 'in open mpi branch'
                maj_ver_i = odata.find('1.')
                maj_ver = odata[maj_ver_i:].split('.')[0]
                min_ver_i = odata.find(maj_ver)
                minor_ver = odata[min_ver_i + len(maj_ver) + 1:].split()[0]
                print 'Version Open MPI 1.%s.%s' % (maj_ver, minor_ver)
                versions.append('.'.join(['ompi-1', maj_ver, minor_ver]))
            #else:
            #    raise
        except:
            print 'failure for cmd: %s' % ' '.join(c)
            print versions
            #raise
    print versions
    # try appropriate variants of launching processes on particular cores
    for v in versions:
        if v == 'sgi':
            nodes = ','.join([k[0] for k in lon])
            new_env = os.environ
            new_env.update({'MPI_DSM_CPULIST':'3,7,4,5:1-3'})
            #new_env.update({'MPI_DSM_CPULIST':'3,7,4,5:' + lon[0][0]})
            #new_env.update({'MPI_DSM_CPULIST':'3,7,4,5'})
            l_str = ['mpirun', lon[1][0], '4', './topo_check', ':', lon[0][0], '3', './topo_check']
            print l_str
            process = subprocess.Popen(l_str, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       env=new_env)
            process.wait()
            odata = process.communicate()[0]
            print odata
        # add elif clauses here....
        else:
            l_str = []
            procs = []
            k = 0
            for n in lon:
                for c in n:
                    k += 1
                    l_str.append(['mpirun', '-bind-to-core', '-bycore',
                                  '-np', '1', 'topo_check_long'])

                    try:
                        print l_str[-1]
                        f = open('blah' + str(k), 'w')
                        procs.append(subprocess.Popen(l_str[-1],
                                                      stdout=f,
                                                      stderr=subprocess.STDOUT))
                    except:
                        print 'FAILED: l_str = ', l_str[-1]
                        raise
            for p in procs:
                p.wait()


def test_mpiexec_mpt(nodes, ppn, mixed_nodes, lon):
    """
    tests the mpiexec_mpt options provided under different implementations
    """
    print "\n****\n"
    # get the version of mpirun (mpirun -v, mpirun --version)
    cmds = [['mpiexec_mpt', '-v']]
    versions = []
    for c in cmds:
        try:
            process = subprocess.Popen(c, stdout=subprocess.PIPE, stderr = subprocess.STDOUT)
            process.wait()
            odata = process.communicate()[0]
            print odata
            #print odata.find('m')
            if odata.find('SGI') >= 0:
                versions.append('sgi')
            #else:
            #    raise
        except:
            print 'failure for cmd: %s' % ' '.join(c)
            print versions
            raise
    print versions
    # try appropriate variants of launching processes on particular cores
    for v in versions:
        if v == 'sgi':
            nodes = ','.join([k[0] for k in lon])
            new_env = os.environ
            new_env.update({'MPI_DSM_CPULIST':'3-7:1-3'})
            l_str = ['mpiexec_mpt', '-np', '8', './topo_check']
            print l_str
            process = subprocess.Popen(l_str, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT,
                                       env=new_env)
            process.wait()
            odata = process.communicate()[0]
            print odata
        # add elif clauses here....

def test_mpiexec(nodes, ppn, mixed_nodes, lon):
    """
    tests the mpiexec options provided under different implementations
    """
    # get the version of mpiexec (???)

    # try appropriate variants of launching processes on particular cores

if __name__ == "__main__":
    print "Starting resource detection test....\n\n"
    recommendations = []
    """
    try:
        test_get_checkjob_info()
        recommendations.append('checkjob')
    except:
        pass
    print "\n\n"
    try:
        test_get_qstat_jobinfo()
        recommendations.append('qstat')
    except:
        pass
    print "\n\n"
    """
    try:
        nodes, ppn, mixed_nodes, lon = test_get_qstat_jobinfo2()
        recommendations.append('qstat2')
        test_mpirun(nodes, ppn, mixed_nodes, lon)
        #test_mpiexec_mpt(nodes, ppn, mixed_nodes, lon)
    except:
        raise
        #pass
    print "\n\n"
    """
    try:
        test_get_pbs_info()
        recommendations.append('pbs')
    except:
        pass
    print "\n\n"
    try:
        test_get_slurm_info()
        recommendations.append('slurm')
    except:
        pass
    """
    print "\n\n"
    print "Recommended approaches:", recommendations
    print "Verify results!"
