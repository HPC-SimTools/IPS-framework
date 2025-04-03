#!/usr/bin/env python3
"""
    The platform configuration file is used to specify the resources available
    to the framework for a given platform.
"""
# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import os
import sys

from .messages import Message


def get_share_and_platform(platform_file_name, ipsPathName):
    if platform_file_name:
        return platform_file_name, ''
    else:
        ipsPDir0 = os.path.dirname(ipsPathName)
        ipsPDir1 = os.path.dirname(ipsPDir0)
        ipsPDir2 = os.path.dirname(ipsPDir1)
        # This is if we've installed it
        pconf = os.path.join('share', 'platform.conf')
        if os.path.exists(os.path.join(ipsPDir1, pconf)):
            ipsShareDir = os.path.join(ipsPDir1, 'share')
        # This is looking in the build directory.
        elif os.path.exists(os.path.join(ipsPDir2, pconf)):
            ipsShareDir = os.path.join(ipsPDir2, 'share')
        else:
            print("Need to specify a platform file")
            sys.exit(Message.FAILURE)
        platform_file_name = os.path.join(ipsShareDir, 'platform.conf')
        return os.path.abspath(platform_file_name), ipsShareDir



# String template used to generate the platform configuration file
# for ensemble instances.
platform_config_template = """
HOST = $hostname
MPIRUN = $mpirun # eval

#######################################
# resource detection method
#######################################
NODE_DETECTION = $node_detection # checkjob | qstat | pbs_env | slurm_env | manual

#######################################
# manual allocation description
#######################################
TOTAL_PROCS = $total_procs
NODES = $nodes
PROCS_PER_NODE = $procs_per_node

#######################################
# node topology description
#######################################
CORES_PER_NODE = $cores_per_node
SOCKETS_PER_NODE = $sockets_per_node

#######################################
# framework setting for node allocation
#######################################
# MUST ADHERE TO THE PLATFORM'S CAPABILITIES
#   * EXCLUSIVE : only one task per node
#   * SHARED : multiple tasks may share a node
# For single node jobs, this can be overridden allowing multiple
# tasks per node.
NODE_ALLOCATION_MODE = $node_allocation_mode # SHARED | EXCLUSIVE
"""