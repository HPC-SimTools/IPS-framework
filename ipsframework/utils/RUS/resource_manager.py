# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Resource Usage Simulator (RUS)
------------------------------

by Samantha Foley, Indiana University
3/4/2010

This RUS simulates the resource usage of a MCMD application as described
by the input files.  It is a tool that helps to determine what resource
allocation algorithms and component configurations work best for classes
of applications.
"""

import sys, os

# import getopt
from configobj import ConfigObj
from time import gmtime, strftime, asctime
from math import ceil
import fault_events

# from rus import framework
# from simulation import simulation
# from component import component
import random


# ===============================================================================
# # resource management
# ===============================================================================
class resource_mgr:
    def __init__(self, fwk, res_file):
        """
        The resource manager models the resource manager in the IPS.  It implements the same allocation policies, however the interface is slightly different and the nodes are internally represented as a count, not individual entries.  Additionally, the resource manager has methods related to fault tolerance that are not currently in the production resource manager implementation in the IPS.
        """
        # =======================================================================
        # # list of all resources allocated to the simualtion
        # =======================================================================
        self.nodes = 0
        self.ppn = 0
        self.memory_per_node = 0
        self.disk_per_node = 0
        self.available = {}  # dictionary containing the amount of resources currently available
        self.allocated = {}  # dictionary containing the amount of resources currently allocated
        self.active = []  # list of component and node count pairs
        self.fwk = fwk
        self.res_file = res_file
        # =======================================================================
        # # read in resource file
        # =======================================================================
        try:
            resources = ConfigObj(res_file, file_error=True, interpolation='template')
        except IOError as xxx_todo_changeme:
            (ex) = xxx_todo_changeme
            print('Error opening/finding resource file %s' % res_file)
            print('ConfigObj error message: ', ex)
            raise
        except SyntaxError as xxx_todo_changeme1:
            (ex) = xxx_todo_changeme1
            print('Syntax problem in resource file %s' % res_file)
            print('ConfigObj error message: ', ex)
            raise
        # print resources

        # =======================================================================
        # # put resources into structures that make sense
        # =======================================================================
        try:
            self.machine_name = resources['machine_name']
            self.nodes = int(resources['nodes'])
            self.ppn = int(resources['ppn'])
            self.memory_per_node = int(resources['mem_pernode'])
            self.disk_per_node = int(resources['disk_pernode'])

            self.available.update({'nodes': self.nodes})
            self.allocated.update({'nodes': 0})
        except:
            print('problems populating resource information into data structures')
            raise

        try:
            self.fwk.mtbf = int(resources['mtbf'])
        except:
            self.fwk.mtbf = -1

        try:
            self.fwk.distribution = resources['distribution']
            # print self.fwk.distribution
        except:
            print('no dist specified')
            self.fwk.distribution = ''

        if self.fwk.distribution == 'weibull':
            try:
                self.fwk.shape = float(resources['shape'])
            except:
                self.fwk.shape = 0.7

    def resubmit(self):
        """
        Simulate a new batch allocation by resetting the node count and availability.
        """
        if self.allocated['nodes'] > 0:
            print('!!!!!!!!!!!!!! some nodes occupied when it is time to resubmit')
            for c, n in self.active:
                print(c.name, n)
        self.nodes = self.fwk.allocation_size
        self.available['nodes'] = self.nodes
        self.allocated['nodes'] = 0

    def get_curr_usage(self):
        """
        Returns the number of nodes allocated and the total number of nodes.  This is used by the logging mechanism in the framework.
        """
        return self.allocated['nodes'], self.nodes

    def get_allocation(self, comp, num_proc, mem_pproc, disk_pproc):
        """
        If there are enough available nodes, the number of nodes allocated is returned.  Otherwise, there are not enough nodes, and -1 is returned.
        """
        nodes = int(ceil(num_proc / float(self.ppn)))

        if self.available['nodes'] >= nodes:
            self.available['nodes'] = self.available['nodes'] - nodes
            self.allocated['nodes'] = self.allocated['nodes'] + nodes
            self.active.append((comp, nodes))
            return nodes
        else:
            return -1

    def failed_node(self):
        """
        removes a node from the allocation and returns the task that must die
        """
        if not self.fwk.failures_on:
            print('tried to make stuff fail :(')
            return -1
        task_to_die = self.get_failed_task()
        if self.fwk.debug and task_to_die:
            print('task to die:', task_to_die.name)
        if task_to_die:
            # ===================================================================
            # # there is a task using the node
            # ===================================================================
            self.allocated['nodes'] -= 1
        else:
            # ===================================================================
            # # no task is using the node
            # ===================================================================
            self.available['nodes'] -= 1
        self.nodes -= 1
        return task_to_die

    def get_failed_task(self):
        """
        randomly chooses a task based on the ones running and how many nodes they are using
        """
        if self.fwk.failure_mode == 'sandia':
            return self.active[0][0]

        # print self.active
        try:
            # make list of tuples (comp, fraction of nodes owned)
            to_choose = [(i, float(j) / self.nodes) for i, j in self.active]
            # add one for unoccupied nodes
            to_choose.append((None, float(self.available['nodes']) / self.nodes))

            # this will choose a component (or None) whose node is the one to die
            n = random.uniform(0, 1)
            for comp, weight in to_choose:
                if n < weight:
                    break
                n = n - weight
            return item

        except:
            print('problem getting failed task')
            print(self.nodes)
            print(self.allocated['nodes'])
            print(self.available['nodes'])
            print('more info in', self.fwk.rlfname)
            raise

    def release_allocation(self, comp, nodes, failed=False):
        """
        releases the resources allocated to the indicated component
        """
        for c, n in self.active:
            if c == comp:
                self.active.remove((c, n))
        self.available['nodes'] = self.available['nodes'] + nodes
        self.allocated['nodes'] = self.allocated['nodes'] - nodes
        if self.available['nodes'] < 0:
            print('impossible situation!!! negative available nodes')
            raise


# end resource manager
