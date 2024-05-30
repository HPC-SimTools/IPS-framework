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
import getopt
from configobj import ConfigObj
from time import gmtime, strftime, asctime

# from simulation import simulation
from resource_manager import resource_mgr
import random
import time


class overhead:
    # def __init__(self, fwk, sim, phase, name, nproc, runtime, stddev, deps, start_up, clean_up)
    def __init__(self, comp, fwk, sim, phase, type, info_dict):
        """
        this object models various overheads associated with the framework,
        simulation, and components.  It resembles a component in some of its
        methods and fields in that it consumes time, but not resources.  Also, these
        do not fail due to node failures.

        """
        # refs to fwk, etc.
        self.fwk = fwk
        self.sim = sim  # if fwk overhead, this will be None
        self.comp = comp  # if sim or fwk overhead, this will be None

        if sim:
            self.sim_name = sim.name
        else:
            self.sim_name = None

        # component properties
        if comp:
            self.phase = phase  # if not comp overhead, this will be None
            self.comp_name = comp.name
        else:
            self.comp_name = None
            self.phase = None
        self.type = type
        self.state = 'not_done'
        self.curr_exec_time = 0
        self.name = ''
        self.runtime = 0
        self.stddev = 0
        self.ready_for_step = 0

        # component stats
        self.total_time = 0  # total productive CPU second usage
        self.num_invocations = 0

        # random number generator for randomness
        self.my_rand = random.Random()
        try:
            self.myseed = self.fwk.my_rand.random()
        except:
            self.myseed = time.time()
        self.my_rand.seed(self.myseed)

        # ----------------------------------------------------
        # mandatory parameters in one try/except blocks
        # ----------------------------------------------------
        try:
            self.name = info_dict['name']
        except:
            self.name = type
        try:
            self.runtime = int(info_dict['runtime'])
        except:
            if self.fwk.debug:
                print('no runtime for overhead %s' % self.name)
        try:
            self.stddev = int(info_dict['stddev'])
        except:
            self.stddev = 0

        # done with initialization, ready to go
        self.ready_for_step = 1

    def get_curr_exec_time(self):
        """
        Returns a newly generated execution time based on the configuration file specification.
        """
        self.start_exec_time = self.fwk.fwk_global_time
        try:
            if self.stddev == 0:
                self.curr_exec_time = self.runtime
            else:
                self.curr_exec_time = self.my_rand.gauss(self.runtime, self.stddev)
        except:
            self.curr_exec_time = self.runtime

    def run(self):
        """
        An exeuction time is obtained and the state is set to *running*.
        """
        # non-resource consuming component
        self.get_curr_exec_time()
        self.state = 'running'
        self.fwk.logEvent(self.sim_name, self.comp_name, 'start_task', 'started overhead phase %s' % (self.name))
        self.num_invocations += 1

    def report_total_usage(self):
        """
        total time spent computing this iteration times the number of processors used is added to the total usage
        """
        self.total_time += self.fwk.fwk_global_time - self.start_exec_time
        # self.sim.num_ckpts += 1
        # self.ready_for_step += 1

    def finish_task(self):
        """
        Usage is recorded, and internal data updated.
        """
        self.report_total_usage()
        self.state = 'done'
        self.curr_exec_time = 0
        self.start_exec_time = -1
        # log message
        self.fwk.logEvent(self.sim_name, self.comp_name, 'finish_task', 'finished overhead %s' % self.name)


# end overhead object
