#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
'''
Resource Usage Simulator (RUS)
------------------------------

by Samantha Foley, Indiana University
3/4/2010

This RUS simulates the resource usage of a MCMD application as described
by the input files.  It is a tool that helps to determine what resource
allocation algorithms and component configurations work best for classes
of applications.

'''

import sys, os
import getopt
from configobj import ConfigObj
from time import gmtime, strftime, asctime
#from simulation import simulation
from resource_manager import resource_mgr
from overhead import overhead
import random
import time

class component():
    #def __init__(self, fwk, sim, phase, name, nproc, runtime, stddev, deps, start_up, clean_up)
    def __init__(self, info_dict, fwk, sim, phase):
        """
        The component models the execution and resource consumption aspects of components and tasks in the IPS.  In this implementation of RUS, there is a 1-to-1 correspondence between components and tasks.
        """
        # refs to fwk, etc.
        self.RM = fwk.RM
        self.fwk = fwk
        self.sim = sim

        # component properties
        self.phase = phase
        self.state = "not_done"
        self.curr_exec_time = 0
        self.name = ''
        self.nproc = 0
        self.runtime = 0
        self.stddev = 0
        self.ready_for_step = 0
        self.using = usage_info()
        self.retry = False
        self.my_overheads = dict()

        # component stats
        self.total_usage = 0  # total productive time
        self.total_time = 0   # total productive CPU second usage
        self.total_rework_time = 0    # total time spent doing rework (including useless rework)
        self.total_rework_usage = 0   # total CPU seconds spent doing rework (including useless rework)
        self.total_ckpt_time = 0    # total time spent doing ckpt (including failed ckpts)
        self.total_ckpt_usage = 0   # total CPU seconds spent doing ckpt (including failed ckpts)
        self.total_restart_time = 0    # total time spent doing restart (including useless restart)
        self.total_restart_usage = 0   # total CPU seconds spent doing restart (including useless restart)
        self.total_waiting_time = 0   # total time spent waiting on resources
        self.start_waiting_time = -1   # start of current waiting period
        self.num_retries = 0  # total number of retries for this component
        self.curr_retries = 0  # total number of retries for this step of the component
        self.num_faults = 0   # total number of faults encountered by this component
        self.num_waiting = 0  # total number of times this component had to wait for more resources

        # random number generator for randomness
        self.my_rand = random.Random()
        try:
            self.myseed = self.fwk.my_rand.random()
        except:
            self.myseed = time.time()
        self.my_rand.seed(self.myseed)

        #----------------------------------------------------
        # mandatory parameters in one try/except blocks
        #----------------------------------------------------
        try:
            self.name = info_dict['name']
            self.nproc = int(info_dict['num_proc'])
            self.runtime = int(info_dict['runtime'])
            self.stddev = int(info_dict['stddev'])
        except:
            raise

        #----------------------------------------------------
        # optional parameters in separate try/except blocks
        #----------------------------------------------------
        try:
            self.type = info_dict['type']
        except:
            self.type = 'normal'

        try:
            self.mem_pproc = int(info_dict['mem_pproc'])
        except:
            self.mem_pproc = 0

        try:
            self.disk_pproc = int(info_dict['disk_pproc'])
        except:
            self.disk_pproc = 0

        try:
            self.desc = info_dict['description']
        except:
            self.desc = ''

        try:
            startup = info_dict['startup']
            self.my_overheads.update({'startup':overhead(self, self.fwk, self.sim, self.phase, 'startup', startup)})
        except:
            self.my_overheads.update({'startup':None})

        try:
            savestate = info_dict['savestate']
            self.my_overheads.update({'savestate':overhead(self, self.fwk, self.sim, self.phase, 'savestate', savestate)})
        except:
            self.my_overheads.update({'savestate':None})

        try:
            self.depends_on = info_dict['depends_on']
            if self.depends_on == '':
                self.depends_on = []
            elif not isinstance(self.depends_on, list):
                self.depends_on = [self.depends_on]
        except:
            self.depends_on = []

        self.ready_for_step = 1

    def get_curr_exec_time(self):
        """
        Returns a newly generated execution time based on the configuration file specification.
        """
        if self.type == 'normal':
            try:
                self.curr_exec_time = self.my_rand.gauss(self.runtime, self.stddev)
            except:
                if self.fwk.debug:
                    print "not varying the execution time"
                self.curr_exec_time = self.runtime
                raise
            self.start_exec_time = self.fwk.fwk_global_time
            self.state = "running"
        elif self.type == 'sandia_work':
            # this is a sandia style work task
            next_ckpt = self.sim.next_ckpt  # relative work time
            work_todo = self.sim.total_work - self.sim.completed_work
            self.curr_exec_time = min(work_todo, next_ckpt)
            self.start_exec_time = self.fwk.fwk_global_time
            self.state = "running"
        elif self.type == 'sandia_rework':
            next_ckpt = self.sim.next_ckpt  # relative work time
            self.curr_exec_time = min(self.sim.rework_todo, next_ckpt)
            self.start_exec_time = self.fwk.fwk_global_time
            self.state = "running"
        elif self.type == 'sandia_ckpt' or self.type == 'sandia_restart':
            self.curr_exec_time = self.runtime
            self.start_exec_time = self.fwk.fwk_global_time
            self.state = "running"
        else:
            print 'error error error!!!  problem with component type in get_curr_exec_time'
            raise

    def run(self):
        """
        The framework calls this method on ready components.  If the component is able to obtain enough resources to run, the state is set to *running*, an execution time is set, and bookkeeping is done.
        """

        if self.nproc > 0:
            # get resources
            nodes = self.RM.get_allocation(self, self.nproc, self.mem_pproc, self.disk_pproc)

            # did we actually get nodes?????
            if nodes >= 0:
                #--------------------------------
                # update resource usage
                #--------------------------------
                self.using.nodes = nodes
                self.using.procs = self.nproc
                if self.start_waiting_time >= 0:
                    self.total_waiting_time += self.fwk.fwk_global_time - self.start_waiting_time
                    self.start_waiting_time = -1

                #--------------------------------
                # set curr_exec_time, start_exec_time, and state
                #--------------------------------
                self.get_curr_exec_time()

                #--------------------------------
                # log event
                #--------------------------------
                if self.retry == True:
                    if self.sim.retry_limit > 0 and self.curr_retries < self.sim.retry_limit:
                        self.num_retries += 1
                        self.curr_retries += 1
                        self.fwk.logEvent(self.sim.name, self.name, "relaunch_task", "relaunched attempt %d on %d processes on %d nodes" %(self.retry, self.using.procs, self.using.nodes))
                    else:
                        #print "exceeded retry limit"
                        if self.fwk.debug:
                            print 'exceeded retry limit, killing sim from component.'
                        self.sim.kill()
                else:
                    self.fwk.logEvent(self.sim.name, self.name, "start_task", "started running on %d processes on %d nodes" % (self.using.procs, self.using.nodes))
            else:
                #-------------------------------------------
                # we did not get the resources we wanted
                #-------------------------------------------
                self.state = "waiting_on_resources"
                if self.start_waiting_time == -1:
                    self.start_waiting_time = self.fwk.fwk_global_time
                    self.num_waiting += 1
                #--------------------------------
                # log event
                #--------------------------------
                self.fwk.logEvent(self.sim.name, self.name, "waiting_on_procs", "needs %d procs %d memory pproc %d disk pproc" % (self.nproc, self.mem_pproc, self.disk_pproc))
        else:
            # non-resource consuming component
            self.get_curr_exec_time()
            if self.retry == True:
                self.fwk.logEvent(self.sim.name, self.name, "relaunch_task", "relaunched, attempt %d" %(self.num_retries))
            else:
                self.fwk.logEvent(self.sim.name, self.name, "start_task", "started")


    def report_total_usage(self):
        """
        At the end of a task execution, usage data is updated.
        """
        work_time = 0
        if self.type == 'normal':
            work_time = self.fwk.fwk_global_time - self.start_exec_time
        elif self.type == 'sandia_work':
            self.total_time += self.fwk.fwk_global_time - self.start_exec_time
            self.total_usage = self.total_time * self.nproc
            if self.state == "running":
                # update total work done
                self.sim.completed_work += self.fwk.fwk_global_time - self.start_exec_time
            elif self.state == "failed":
                # add this work to the work to be redone
                self.sim.rework_todo += self.fwk.fwk_global_time - self.start_exec_time
                self.state = "not_ready"
                self.num_faults += 1
        elif self.type == 'sandia_rework':
            self.total_rework_time += self.fwk.fwk_global_time - self.start_exec_time
            self.total_rework_usage = self.total_rework_time * self.nproc
            if self.state == "running":
                # update total work done
                self.sim.next_ckpt = self.sim.ckpt_interval - (self.fwk.fwk_global_time - self.start_exec_time)
                self.sim.rework_todo -= self.fwk.fwk_global_time - self.start_exec_time
            elif self.state == "failed":
                # add this work to the work to be redone
                self.state = "not_ready"
                self.num_faults += 1
        elif self.type == 'sandia_ckpt':
            self.total_ckpt_time += self.fwk.fwk_global_time - self.start_exec_time
            self.total_ckpt_usage = self.total_ckpt_time * self.nproc
            if self.state == "running":
                # update last ckpt
                self.sim.last_ckpt = self.sim.completed_work
            elif self.state == "failed":
                # add work to rework
                self.sim.rework_todo += self.sim.next_ckpt
                self.state = "not_ready"
                self.num_faults += 1
        elif self.type == 'sandia_restart':
            print "time spent in rework", self.fwk.fwk_global_time - self.start_exec_time
            self.total_restart_time += self.fwk.fwk_global_time - self.start_exec_time
            self.total_restart_usage = self.total_restart_time * self.nproc
            #if self.state == "running":
                # nothing to do?
            #    pass
            if self.state == "failed":
                # gotta try again
                self.state = "ready"
                self.num_faults += 1
        else:
            print "problems updating state in report_total_usage"
            raise
        if self.type == 'normal':
            if self.sim.state == 'rework':
                self.total_rework_time += work_time
                self.total_rework_usage = self.total_rework_time * self.nproc
            else: # sim.state == 'work'
                if self.retry:
                    self.total_rework_time += work_time
                    self.total_rework_usage = self.total_rework_time * self.nproc
                else:
                    self.total_time += work_time
                    self.total_usage = self.total_time * self.nproc

    def kill_task(self):
        """
        This is called when there are running tasks during a restart or resubmit event.  Resources are released, and bookkeeping is done.
        """
        if self.using.nodes > 0:
            if self.state == "failed":
                self.RM.release_allocation(self, self.using.nodes - 1, failed=True)
            else:
                self.RM.release_allocation(self, self.using.nodes)
            self.fwk.logEvent(self.sim.name, self.name, "finish_task", "task killed due to simulation failure")
        else:
            print 'trying to kill task %s that has no nodes allocated (%d)' % (self.name, self.using.nodes)
            print "problems!"
            self.fwk.logEvent(self.sim.name, self.name, "finish_task", "@@@@task killed due to simulation failure")
            raise
        self.report_total_usage()
        self.using.clear()
        self.retry = False
        self.curr_retries = 0
        self.curr_exec_time = 0
        # log message
        self.state = "not_done"
        self.ready_for_step = 0

    def finish_task(self):
        """
        This is called when a task finished successfully to release its resources and update internal data.
        """
        self.report_total_usage()
        if self.retry:
            self.retry = False
            self.curr_retries = 0
        self.state = "done"
        self.ready_for_step += 1
        self.RM.release_allocation(self, self.using.nodes)
        self.using.clear()
        self.curr_exec_time = 0
        # log message
        self.fwk.logEvent(self.sim.name, self.name, "finish_task", "finished running")

    def failed_task(self):
        """
        This is called when a task finished successfully to release its resources and update internal data.
        """
        self.report_total_usage()
        #print 'failure killed task %s from sim %s' % (self.name, self.sim.name)
        self.num_faults += 1
        self.retry = True
        self.state = "ready"
        if self.using.nodes > 0:
            self.RM.release_allocation(self, self.using.nodes - 1, failed=True)
        self.using.clear()
        self.curr_exec_time = 0
        self.fwk.logEvent(self.sim.name, self.name, "failed_task", "task failed due to node failure")

# end component object

class usage_info():
    def __init__(self):
        """
        storage object for resource data.  Only ``nodes`` and ``procs`` are used, currenly.
        """
        self.nodes = 0
        self.procs = 0
        self.disk = 0
        self.memory = 0

    def clear(self):
        self.nodes = 0
        self.procs = 0
        self.disk = 0
        self.memory = 0

# end usage info object
