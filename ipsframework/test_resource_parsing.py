# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
utility to help test resource parsing functions from resourceHelper

Notes:
  - These functions should not be dependent on anything from the framework.
  - Failed parsing will result in a message indicating the method does not work.
    You may want to turn on the exceptions and examine the output from the command
    to see if there was a change in how the output is presented, and thus problems
    parsing.

"""

from resourceHelper import get_checkjob_info, get_qstat_jobinfo, get_pbs_info, get_slurm_info, get_qstat_jobinfo2


def test_get_checkjob_info():
    try:
        print('Testing get_checkjob_info:')
        n, ppn, mixed_nodes, lon = get_checkjob_info()
        print('get_checkjob_info yields {} nodes and {} ppn'.format(n, ppn))
        for name, p in lon:
            print('\t%s: %d' % (name, p))
    except:
        print('get_checkjob_info does not work on this machine')
        raise


def test_get_qstat_jobinfo():
    try:
        print('Testing get_qstat_jobinfo:')
        n, ppn, mixed_nodes, lon = get_qstat_jobinfo()
        print('get_qstat_jobinfo yields %d nodes and %d ppn ' % (n, ppn))
        for name, p in lon:
            print('\t%s: %d' % (name, p))
    except:
        print('get_qstat_jobinfo does not work on this machine')
        raise


def test_get_qstat_jobinfo2():
    try:
        print('Testing get_qstat_jobinfo2:')
        n, ppn, mixed_nodes, lon = get_qstat_jobinfo2()
        print('get_qstat_jobinfo2 yields %d nodes and %d ppn ' % (n, ppn))
        for name, l in lon:
            print('\t%s: ' % name, l)
    except:
        print('get_qstat_jobinfo2 does not work on this machine')
        raise


def test_get_pbs_info():
    try:
        print('Testing get_pbs_info:')
        nodes, ppn, mixed_nodes, lon = get_pbs_info()
        print('get_pbs_info yields %d nodes and %d ppn ' % (nodes, ppn))
        for name, p in lon:
            print('\t%s: %d' % (name, p))

    except:
        print('get_pbs_info does not work on this machine')
        raise


def test_get_slurm_info():
    try:
        print('Testing get_slurm_info:')
        nodes, ppn, mixed_nodes, lon = get_slurm_info()
        print('get_slurm_info yields %d nodes and %d ppn ' % (nodes, ppn))
        for name, p in lon:
            print('\t%s: %d' % (name, p))

    except:
        print('get_slurm_info does not work on this machine')
        raise


if __name__ == "__main__":
    print("Starting resource detection test....\n\n")
    recommendations = []
    try:
        test_get_checkjob_info()
        recommendations.append('checkjob')
    except:
        pass
    print("\n\n")
    try:
        test_get_qstat_jobinfo()
        recommendations.append('qstat')
    except:
        pass
    print("\n\n")
    try:
        test_get_qstat_jobinfo2()
        recommendations.append('qstat2')
    except:
        pass
    print("\n\n")
    try:
        test_get_pbs_info()
        recommendations.append('pbs')
    except:
        pass
    print("\n\n")
    try:
        test_get_slurm_info()
        recommendations.append('slurm')
    except:
        pass
    print("\n\n")
    print("Recommended approaches:", recommendations)
    print("Verify results!")
