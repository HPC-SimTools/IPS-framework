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

from configobj import ConfigObj
from component import component
from overhead import overhead
from phase import phase


class simulation():
    def __init__(self, info_dict, fwk, index):
        """
        construct and manage the workflow of a simulation and its constituent components
        """

        # stuff from the framework
        self.RM = fwk.RM
        self.fwk = fwk

        # bookkeeping
        self.total_usage = 0
        self.total_work_time = 0
        self.total_lost_time = 0
        self.total_overhead = 0
        self.total_restart_time = 0
        self.total_resubmit_time = 0
        self.total_launch_delay = 0
        self.total_rework_time = 0
        self.total_ckpt_time = 0
        self.total_waiting_time = 0
        self.num_waiting = 0
        self.num_restarts = 0
        self.num_rework = 0
        self.num_work = 0
        self.num_ckpts = 0
        self.num_faults = 0
        self.num_retries = 0
        self.resubmissions = 0
        self.last_submission_time = 0

        # my components and properties
        self.state = 'startup' # other states: 'shutdown', 'checkpoint', 'restart', 'work'
        self.my_comps = dict()
        self.all_comps = dict()
        self.my_overheads = dict()
        self.phases = dict()
        self.is_done = False
        self.resubmission_threshold = 5
        try:
            self.name = info_dict['name'] + '_' + str(index)
        except:
            raise

        try:
            self.mode = info_dict['mode']
        except:
            self.mode = 'normal' # this means time stepped

        if self.mode == 'normal':
            self.fwk.failure_mode = 'normal'
            try:
                self.nsteps = int(info_dict['nsteps'])
                self.comp_list = info_dict['components']
            except:
                self.nsteps = 0
                self.comp_list = []

            try:
                self.phase_list = info_dict['phases']
            except:
                self.phase_list = []

            if self.nsteps > 0 and self.comp_list:
                self.old_style = True
            elif self.phase_list:
                self.old_style = False
            else:
                print("bad config file")
                raise

            try:
                self.ft_strategy = info_dict['ft_strategy']
            except:
                self.ft_strategy = None

            try:
                self.retry_limit = int(info_dict['retry_limit'])
            except:
                self.retry_limit = -1

            self.curr_step = 1
            self.curr_phase_index = -1
            self.curr_phase = ''
            self.total_steps = 0

        elif self.mode == 'total_time':
            #self.fwk.failures_on = True
            self.fwk.failure_mode = 'sandia'
            try:
                self.total_work = int(info_dict['total_work'])
                self.comp_list = info_dict['components']
            except:
                raise
            self.rework_todo = 0
            self.completed_work = 0
            self.old_style = True


        # get overheads
        try:
            startup = info_dict['startup']
            self.my_overheads.update({'startup':overhead(None, self.fwk, self, None, 'startup', startup)})
        except:
            self.my_overheads.update({'startup':overhead(None, self.fwk, self, None, 'startup', None)})

        try:
            resubmit = info_dict['resubmit']
            self.my_overheads.update({'resubmit':overhead(None, self.fwk, self, None, 'resubmit', resubmit)})
        except:
            self.my_overheads.update({'resubmit':overhead(None, self.fwk, self, None, 'resubmit', None)})

        try:
            shutdown = info_dict['shutdown']
            self.my_overheads.update({'shutdown':overhead(None, self.fwk, self, None, 'shutdown', shutdown)})
        except:
            self.my_overheads.update({'shutdown':overhead(None, self.fwk, self, None, 'shutdown', None)})

        try:
            restart = info_dict['restart']
            self.my_overheads.update({'restart':overhead(None, self.fwk, self, None, 'restart', restart)})
        except:
            self.my_overheads.update({'restart':overhead(None, self.fwk, self, None, 'restart', None)})

        try:
            launch_delay = info_dict['launch_delay']
            self.my_overheads.update({'launch_delay':overhead(None, self.fwk, self, None, 'launch_delay', launch_delay)})
        except:
            self.my_overheads.update({'launch_delay':overhead(None, self.fwk, self, None, 'launch_delay', None)})


        # is checkpointing being modeled?
        try:
            ckpt_section = info_dict['checkpoint']
            ckpt_on_val = ckpt_section['ckpt_on']
            if ckpt_on_val == 'True':
                self.ckpt_on = True
            else:
                self.ckpt_on = False
        except:
            self.ckpt_on = False

        # get checkpointing parameters
        if self.ckpt_on:
            try:
                self.ckpt_mode = ckpt_section['ckpt_mode']
                if self.ckpt_mode == 'sandia':
                    self.last_ckpt = 0
                    try:
                        self.next_ckpt = int(ckpt_section['tau'])
                        self.ckpt_interval = self.next_ckpt
                    except:
                        # **** NEED TO CHANGE TO CALCULATE INITIAL VAL!!!!
                        self.next_ckpt = 10
                elif self.ckpt_mode == 'wall_regular' or self.ckpt_mode == 'phys_regular':
                    self.ckpt_interval = int(ckpt_section['ckpt_interval'])
                    self.next_ckpt = self.ckpt_interval
                elif self.ckpt_mode == 'wall_explicit' or self.ckpt_mode == 'phys_explicit':
                    self.ckpt_values = [int(x) for x in ckpt_section['ckpt_values']]
                    self.next_ckpt = self.ckpt_values.pop(0)
                self.my_overheads.update({'checkpoint':overhead(None, self.fwk, self, None, 'checkpoint', ckpt_section)})
            except:
                print("problems setting up checkpoint parameters")
                raise
        self.ckpt_comps = list()
        self.ckpt_step = 0
        self.ckpt_phase_index = 0
        self.ckpt_phase = ''

        # add components
        try:
            if self.mode == 'total_time':
                self.phase_list.append('none')
                self.phases.update({'none':phase({}, self.fwk, self, 'none', old_style=True)})
                self.phases['none'].comp_list = self.comp_list
                if not isinstance(self.comp_list, list):
                    self.comp_list = [self.comp_list]
                for s in self.comp_list:
                    self.all_comps.update({'none_'+s:component(info_dict[s], self.fwk, self, 'none')})
            elif self.old_style:
                self.phase_list.append('none')
                self.phases.update({'none':phase({}, self.fwk, self, 'none', old_style=True)})
                self.phases['none'].nsteps = self.nsteps
                self.phases['none'].comp_list = self.comp_list
                if not isinstance(self.comp_list, list):
                    self.comp_list = [self.comp_list]
                for s in self.comp_list:
                    self.all_comps.update({'none_'+s:component(info_dict[s], self.fwk, self, 'none')})
            else:
                if not isinstance(self.phase_list, list):
                    self.phase_list.append(self.phase_list)
                for p in self.phase_list:
                    self.phases.update({p:phase(info_dict[p], self.fwk, self.name, p)})
                    if not isinstance(self.phases[p].comp_list, list):
                        self.phases[p].comp_list = [self.phases[p].comp_list]
                    for s in self.phases[p].comp_list:
                        self.all_comps.update({p + '_' + s:component(info_dict[p][s], self.fwk, self, p)})
        except:
            raise

        if self.fwk.debug:
            for k, v in list(self.phases.items()):
                print("phase:", k, "nsteps:", v.nsteps, "comps:", v.comp_list)
                for c in list(self.all_comps.values()):
                    print(c.name, c.nproc, c.runtime, c.stddev)
        self.get_next_phase()

        # populate handles to total_time components
        if self.mode == 'total_time':
            for c in list(self.my_comps.values()):
                if c.type == 'sandia_work':
                    self.work_comp = c
                    self.work_comp.state = "ready"
                elif c.type == 'sandia_rework':
                    self.rework_comp = c
                elif c.type == 'sandia_restart':
                    self.restart_comp = c
                elif c.type == 'sandia_ckpt':
                    self.ckpt_comp = c

        #self.get_ready_comps()
        if self.fwk.debug:
            print(list(self.my_comps.keys()))


    def get_ready_comps(self):
        """
        Cycles through the comps in ``self.my_comps``, checks for dependencies,
        and returns those that are ready.
        """
        # ***** need to change to incorporate component overheads!!!!
        ready_comps = list()
        #print "in get ready comps"
        if self.mode == "total_time":
            for c in list(self.my_comps.values()):
                if c.state == "ready":
                    return [c]
        for c in list(self.my_comps.values()):
            #print c.name, c.state
            # update the waiting on parents components
            if isinstance(c, component):
                """
                if c.ready_for_step < self.ckpt_step:
                    print 'ready for step less than last checkpoint!!!  comp: %s - %d ckpt: %d, curr:%d\n\n' % (c.name, c.ready_for_step, self.ckpt_step, self.curr_step)
                    self.fwk.logEvent(self.name, None, 'badness', 'ready for step less than last checkpoint!!!  comp: %s - %d ckpt: %d, curr:%d\n\n' % (c.name, c.ready_for_step, self.ckpt_step, self.curr_step))
                """
                if (c.state == "waiting_on_parents") or (c.state == "not_done"):
                    c.state = "ready"
                    parents = c.depends_on
                    for p in parents:
                        if not (self.my_comps[c.phase + '_' + p].state == "done"):
                            c.state = "waiting_on_parents"
                            self.fwk.logEvent(self.name, c.name, "waiting_on_parents", "waiting on (at least one) parents")

                if c.state == "ready":
                    ready_comps.append(c)
            else:
                #print "comp in my_comps:", c.name, c.state
                #if c.state == "ready":
                #    ready_comps.append(c)
                ready_comps.append(c)
        return ready_comps

    def get_running_comps(self):
        """
        returns all comps and overheads that are in the state "running"
        """
        r = list()
        for o in list(self.my_overheads.values()):
            if o and o.state == "running":
                r.append(o)
        for c in list(self.my_comps.values()):
            if c.state == "running":
                r.append(c)
        return r

    def update_step(self):
        """
        This function determines if we are ready for a new step and in
        the process checks for other conditions too..

        The return value is True if we need to do a checkpoint now, and False otherwise.

        * if the state of the simulation is *failed*, then we set ``self.is_done`` to True, and return False
        * see if we are ready for the next step, if not, return False; otherwise, continue.
        * if checkpointing is turned on, we see if it is time to checkpoint, if so, return True
        * set ``self.curr_step`` to new step
        * see if it is time to change the state from *rework* to *work*, do so if necessary
        * if it is time for a new phase, get the new phase (see get_next_phase())
        * if not done, set ``self.my_comps`` to *not_done* and ``comp.ready_for_step`` to new step

        """
        #---------------
        #  set next step
        #---------------
        next_step = self.curr_step + 1
        #--------------
        #  did we fail?
        #--------------
        if self.state == "failed":
            self.fwk.logEvent(self.name, None, 'all_fail', 'simulation failed before completing its work')
            if self.fwk.debug:
                print(" ##### failed", self.fwk.fwk_global_time, self.curr_phase, self.curr_step)
                print("bad things happened and now we are shutting down")
            del self.my_comps
            self.my_comps = {}
            #self.state = 'shutdown'
            #self.my_comps.update({'shutdown':self.my_overheads['shutdown']})
            #self.my_comps['shutdown'].state = "ready"
            #if self.fwk.debug:
            #    print "new my comps", self.my_comps.keys()
            self.is_done = True
            return False

        #-----------------------------------------
        #  are we ready for the next step??
        #-----------------------------------------
        for c in list(self.my_comps.values()):
            if isinstance(c, component) and c.ready_for_step < next_step:
                if c.ready_for_step < next_step - 1:
                    print('ready for step not equal to curr step!!! (%s-%s: ready for step: %d -- curr step: %d)' % (c.phase, c.name, c.ready_for_step, self.curr_step))
                    raise
                return False

        #-------------------------------------------------
        # ready to go to the next step
        #  - if ckpt_on, checkpoint if necessary
        #  - check to see if we have entered a new phase
        #-------------------------------------------------

        if self.ckpt_on:
            if self.curr_phase_index == (len(self.phases) - 1) and next_step > self.phases[self.curr_phase].nsteps:
                if self.fwk.debug:
                    print("not checkpointing because it is the last step of the last phase!!!!!!!!!!!!!!!!!!!")
            else:
                if self.ckpt_mode == 'phys_explicit':
                    #print ">",
                    if self.next_ckpt and self.curr_step >= self.next_ckpt:
                        try:
                            self.next_ckpt = self.ckpt_values.pop(0)
                        except:
                            #print "                   &&&&&&&"
                            self.next_ckpt = None
                        return True
                elif self.ckpt_mode == 'phys_regular':
                    if self.curr_step >= self.next_ckpt:
                        self.next_ckpt += self.ckpt_interval
                        return True
                elif self.ckpt_mode == 'wall_explicit':
                    if self.next_ckpt and self.fwk.fwk_global_time >= self.next_ckpt:
                        try:
                            self.next_ckpt = self.ckpt_values.pop(0)
                        except:
                            #print "                   &&&&&&&"
                            self.next_ckpt = None
                        return True
                elif self.ckpt_mode == 'wall_regular':
                    if self.fwk.fwk_global_time >= self.next_ckpt:
                        self.next_ckpt += self.ckpt_interval
                        return True

        self.curr_step = next_step
        #print 'new step for', self.name

        #------------------------------
        # write log message
        #------------------------------
        self.fwk.logEvent(self.name, None, "end_step", "ending step %d" % (self.curr_step - 1))
        if self.fwk.debug:
            print("curr step", self.curr_step, "next phase at", self.phases[self.curr_phase].nsteps, "steps")

        #------------------------------
        # done with rework?
        #------------------------------
        if self.state == "rework" and self.curr_phase == self.rework_done_phase and self.curr_step >= self.rework_done_step:
            #print '>'
            self.state = "work"
            #self.total_rework_time += self.fwk.fwk_global_time - self.start_rework_time
            if self.fwk.debug:
                print(" ##### work", self.fwk.fwk_global_time, self.curr_phase, self.curr_step)
            self.fwk.logEvent(self.name, None, "state_change", "work")

        #------------------------------------------
        # account for newly completed step as work
        #------------------------------------------
        if self.state == 'work':
            self.total_steps += 1
            #print "adding a step", self.curr_step

        #------------------------------
        # ready for next phase?
        #------------------------------
        if self.curr_step > self.phases[self.curr_phase].nsteps:
            # end of phase
            self.curr_step = 1
            self.is_done = self.get_next_phase()

        #------------------------------
        # if not done, set up comps for new step
        #------------------------------
        if not self.is_done:
            #self.fwk.logEvent(self.name, None, "start_step", "starting new step %d" % self.curr_step)
            # set all components to beginning of step
            for c in list(self.my_comps.values()):
                c.state = 'not_done'
                c.ready_for_step = self.curr_step
        return False

    def get_next_phase(self):
        """
        This gets called when there is a transition from one phase to another.

        ``self.mycomps`` is populated with the components from the new phase and initialized.
        """

        #print 'in get next phase'
        #print self.state
        if self.state == 'startup':
            # it is the beginning or time
            self.last_submission_time = self.fwk.fwk_global_time
            if self.fwk.debug:
                print(" ##### startup", self.fwk.fwk_global_time)
                print("in get next phase, it is the beginning of time, so we are doing startup")
            self.my_comps.update({'startup':self.my_overheads['startup']})
            self.my_comps['startup'].state = "ready"
            if self.fwk.debug:
                print("new my comps", list(self.my_comps.keys()))
            self.fwk.logEvent(self.name, None, "state_change", "startup")
            self.fwk.logEvent(self.name, None, "phase_change", "changing from %s to %s" % ('startup', self.curr_phase))
            return False
        elif self.state == 'work' and self.curr_phase_index < len(self.phase_list) - 1:
            # there are more phases
            #  - remove old components
            #  - add new components
            old_phase = self.curr_phase
            self.curr_phase_index += 1
            self.curr_phase = self.phase_list[self.curr_phase_index]
            #self.phase_list.remove(self.curr_phase)
            if self.fwk.debug:
                print("in get next phase, phase_list = ", self.phase_list)
                print("old my comps", list(self.my_comps.keys()))
            del self.my_comps
            self.my_comps = {}
            for n, comp in list(self.all_comps.items()):
                if comp.phase == self.curr_phase:
                    self.my_comps.update({n:comp})
            if self.fwk.debug:
                print("new my comps", list(self.my_comps.keys()))
            self.fwk.logEvent(self.name, None, "phase_change", "changing from %s to %s" % (old_phase, self.curr_phase))
            return False
        elif self.state == 'rework' and self.curr_phase_index < len(self.phase_list) - 1:
            # there are more phases
            #  - remove old components
            #  - add new components
            old_phase = self.curr_phase
            self.curr_phase_index += 1
            self.curr_phase = self.phase_list[self.curr_phase_index]
            if self.fwk.debug:
                print("in get next phase, phase_list = ", self.phase_list)
                print("old my comps", list(self.my_comps.keys()))
            del self.my_comps
            self.my_comps = {}
            for n, comp in list(self.all_comps.items()):
                if comp.phase == self.curr_phase:
                    self.my_comps.update({n:comp})
            if self.fwk.debug:
                print("new my comps", list(self.my_comps.keys()))
            self.fwk.logEvent(self.name, None, "phase_change", "changing from %s to %s" % (old_phase, self.curr_phase))
            return False
        elif (self.state == 'work' or self.state == 'rework') and self.curr_phase_index >= len(self.phase_list) - 1 :
            # no more phases
            old_phase = self.curr_phase
            self.state = 'shutdown'
            if self.fwk.debug:
                print("in get next phase, no more phases, time to shutdown")
                print("old my comps", list(self.my_comps.keys()))
            del self.my_comps
            self.my_comps = {}
            if self.fwk.debug:
                print(" ##### shutdown", self.fwk.fwk_global_time)
            self.fwk.logEvent(self.name, None, "state_change", "shutdown")
            self.my_comps.update({'shutdown':self.my_overheads['shutdown']})
            self.my_comps['shutdown'].state = "ready"
            if self.fwk.debug:
                print("new my comps", list(self.my_comps.keys()))
            self.fwk.logEvent(self.name, None, "phase_change", "changing from %s to %s" % (old_phase, 'shutdown'))
            return False

    def sync(self, global_time_update):
        """
        The framework calls this function to update the finished or failed components,
        and a list of the finished tasks and a list of tasks to run are returned to the framework.

        * ``finish_task()`` and ``failed_task()`` are invoked on components as appropriate
        * ``update_step()`` is called if there are any finished tasks
        * a checkpoint is taken if it is time to take one
        * ``get_next_phase()`` is called if we have completed a phase
        """
        finished_comps = list()
        failed_comps = list()
        nctr = list()
        for o in list(self.my_overheads.values()):
            if o and o.state == "running" and (o.start_exec_time + o.curr_exec_time) <= self.fwk.fwk_global_time:
                """
                the overhead has finished, time to move on to the next thing
                """
                o.finish_task()
                if o.name == 'shutdown':
                    self.fwk.logEvent(self.name, o.name, "end_step", "ending simulation shutdown")
                    self.is_done = True
                    return [o],[]
                elif o.name == 'restart':
                    self.restart_restore_state()
                    return [o], self.get_ready_comps()
                elif o.name == 'startup':
                    self.fwk.logEvent(self.name, o.name, "end_step", "ending simulation startup")
                    self.state = 'work'
                    self.fwk.logEvent(self.name, None, "state_change", "work")
                    self.curr_step = 1
                    del self.my_comps
                    self.my_comps = {}
                    self.is_done = self.get_next_phase()
                    #if self.ckpt_on:
                    self.ckpt_phase = self.curr_phase
                    self.ckpt_phase_index = self.curr_phase_index
                    self.ckpt_step = self.curr_step
                    self.ckpt_fwk_global_time = self.fwk.fwk_global_time
                    #print "new phase", self.curr_phase
                    if not self.is_done:
                        self.fwk.logEvent(self.name, o.name, "start_step", "starting new step %d" % self.curr_step)
                    # set all components to beginning of step
                    for c in list(self.my_comps.values()):
                        c.state = 'not_done'
                    for c in list(self.my_comps.keys()):
                        self.ckpt_comps.append(c)
                    return [o], self.get_ready_comps()
                elif o.name == 'resubmit':
                    self.fwk.logEvent(self.name, o.name, "end_step", "ending simulation resubmit")
                    self.resubmit_restart()
                    return [o], self.get_ready_comps()
                elif o.name == 'checkpoint':
                    self.fwk.logEvent(self.name, o.name, "end_step", "ending simulation checkpoint")
                    finished_comps.append(o)
                elif o.name == 'launch_delay':
                    self.fwk.logEvent(self.name, o.name, "end_step", "ending simulation launch delay")
                    finished_comps.append(o)
                else:
                    print('ack ack ack')
            elif o and o.state == 'ready' and o.name == 'resubmit':
                #print 'time to run resubmit!!!'
                return [], [self.my_overheads['resubmit']]
        for c in list(self.my_comps.values()):
            if c.state == "running" and (c.start_exec_time + c.curr_exec_time) <= self.fwk.fwk_global_time:
                c.finish_task()
                finished_comps.append(c)
            elif c.state == "failed":
                # **** check policy
                #  - task relaunch: c.failed_task
                #  - simulation restart: call restart
                print('before failed_task  - ', self.ft_strategy)
                c.failed_task() # need to keep!!! does accounting for num_faults
                if not (self.state == "work" or self.state == "rework"):
                    print(self.state)
                if self.ft_strategy == "task_relaunch":
                    failed_comps.append(self.my_overheads['launch_delay'])
                elif self.ft_strategy == "sim_cr":
                    print('in ft_strategy = sim_cr')
                    self.restart_setup()
                    failed_comps.append(self.my_overheads['restart'])
                elif self.ft_strategy == "restart":
                    if self.fwk.debug:
                        print('encountered a failure, restarting from the beginning')
                    self.restart_setup()
                    failed_comps.append(self.my_overheads['restart'])
                else:
                    if self.fwk.debug:
                        print('killing simulation from simulation because we do not have a fault tolerance strategy')
                    self.kill()

        if self.mode == 'total_time':
            # are we done?
            if self.completed_work == self.total_work:
                self.is_done = True
                return finished_comps, nctr
            if finished_comps and finished_comps[0] == self.work_comp:
                self.num_work += 1
                self.ckpt_comp.state = 'ready'
                nctr.append(self.ckpt_comp)
            elif finished_comps and finished_comps[0] == self.rework_comp:
                self.num_rework += 1
                self.work_comp.state = 'ready'
                nctr.append(self.work_comp)
            elif finished_comps and finished_comps[0] == self.ckpt_comp:
                self.num_ckpts += 1
                self.work_comp.state = 'ready'
                nctr.append(self.work_comp)
            elif finished_comps and finished_comps[0] == self.restart_comp:
                self.num_restarts += 1
                self.rework_comp.state = 'ready'
                nctr.append(self.rework_comp)
            elif failed_comps and failed_comps[0] == self.work_comp:
                self.num_work += 1
                self.restart_comp.state = 'ready'
                nctr.append(self.restart_comp)
            elif failed_comps and failed_comps[0] == self.rework_comp:
                self.num_rework += 1
                self.restart_comp.state = 'ready'
                nctr.append(self.restart_comp)
            elif failed_comps and failed_comps[0] == self.ckpt_comp:
                self.num_ckpts += 1
                self.restart_comp.state = 'ready'
                nctr.append(self.restart_comp)
            elif failed_comps and failed_comps[0] == self.restart_comp:
                self.num_restarts += 1
                self.restart_comp.state = 'ready'
                nctr.append(self.restart_comp)
        else:
            # add failed components to the to_run list
            nctr.extend(failed_comps)

            # if there are finished components, that means we need to find new comps to run
            if finished_comps:
                time_to_checkpoint = self.update_step()
                if time_to_checkpoint:
                    self.checkpoint()
                    nctr.append(self.my_overheads['checkpoint'])
                else:
                    nctr.extend(self.get_ready_comps())
        return finished_comps, nctr

    def kill(self):
        """
        something went terribly wrong and we must die (gracefully)
        """

        if self.fwk.debug:
            print(" ##### failed", self.fwk.fwk_global_time, self.curr_phase, self.curr_step, list(self.my_comps.keys()))
            print("bad things happened and now we are shutting down")
        for c in list(self.my_comps.values()):
            if isinstance(c, component) and c.using.nodes > 0:
                c.kill_task()
        self.is_done = True
        del self.my_comps
        self.my_comps = {}
        #self.state = 'shutdown'
        #self.my_comps.update({'shutdown':self.my_overheads['shutdown']})
        #self.my_comps['shutdown'].state = "ready"
        self.is_done = True

    def resubmit_setup(self):
        """
        There are not enough nodes to complete the simulation.  The simulation will be
        resubmitted in a new batch allocation and restarted from the last available checkpoint.
        If we have exceeded the maximum allowed resubmissions, the simulation will be killed.
        Current maximum resubmissions is 5.
        """
        if self.fwk.debug:
            print("\n\n ##### resubmitting", self.fwk.fwk_global_time, self.curr_phase, self.curr_step, "\n\n\n")
        # time to resubmit, is that ok?
        #self.num_faults += 1
        if self.resubmissions > self.resubmission_threshold:
            if self.fwk.debug:
                print("too many resubmissions (", self.resubmissions, ")")
            raise
        self.resubmissions += 1
        # setup rework for after restart period
        if self.state == 'work':
            # save current state so we know when we are done doing rework
            self.rework_done_step = self.curr_step
            self.rework_done_phase = self.curr_phase
            self.rework_done_phase_index = self.curr_phase_index
            self.total_lost_time += self.fwk.fwk_global_time - self.ckpt_fwk_global_time
        else:
            #print 'state in resubmit setup:', self.state
            if self.fwk.debug:
                print("failure occured during rework period")

        self.state = 'resubmit'
        # kill any running tasks (really there shouldn't be any)
        for c in list(self.all_comps.values()):
            if c.retry:
                c.retry = False
                c.curr_retries = 0
            #print '  in resub setup  ', c.name, c.state
            if c.using.nodes > 0:
                self.fwk.logEvent(self.name, None, 'blah', 'killing task %s in resubmit setup' % c.name)
                c.kill_task()
        #print "killed tasks"
        del self.my_comps
        self.my_comps = {}
        self.my_comps.update({'resubmit':self.my_overheads['resubmit']})
        #print "ready for next loop"
        self.my_comps['resubmit'].state = 'ready'
        self.my_overheads['resubmit'].state = 'ready'
        self.fwk.logEvent(self.name, None, "end_step", "resubmit terminated step early")

    def resubmit_restart(self):
        """
        After the resubmission has successfully completed, the restart is commenced and other
        counters reset for this new allocation.
        """
        if self.fwk.debug:
            print(" ##### restarting", self.fwk.fwk_global_time, self.curr_phase, self.curr_step)

        # kill running tasks
        self.last_submission_time = self.fwk.fwk_global_time
        self.state = 'restart'
        self.num_restarts += 1
        self.num_rework += 1
        self.total_restart_time += self.my_overheads['restart'].runtime
        self.start_rework_time = self.fwk.fwk_global_time
        self.curr_phase = self.ckpt_phase
        self.curr_phase_index = self.ckpt_phase_index
        self.curr_step = self.ckpt_step
        #self.total_steps = self.curr_step
        if self.fwk.debug:
            print(" ##### rework", self.fwk.fwk_global_time, self.curr_phase, self.curr_step)
        self.fwk.logEvent(self.name, None, 'resubmit_restart', 'resubmit - restarting simulation at step %d' % self.curr_step)
        del self.my_comps
        self.my_comps = {}
        for c in self.ckpt_comps:
            self.my_comps.update({c:self.all_comps[c]})
            self.all_comps[c].ready_for_step = self.curr_step
            self.all_comps[c].state = "not_done"
            self.my_comps[c].ready_for_step = self.curr_step
            self.my_comps[c].state = "not_done"
        self.state = 'rework'

    def checkpoint(self):
        """
        The point from which to restart is saved.
        """
        if self.fwk.debug:
            print(".", end=' ')
        #print " ##### checkpointing", self.fwk.fwk_global_time, self.curr_phase, self.curr_step
        self.fwk.logEvent(self.name, None, 'checkpoint', 'checkpointing simulation at step %d' % self.curr_step)
        self.num_ckpts += 1
        del self.ckpt_comps
        self.ckpt_comps = []
        self.my_overheads['checkpoint'].state = "ready"
        # the current step has been done, saving the state, such that we can resume at the *next* step
        if self.curr_step < self.phases[self.curr_phase].nsteps:
            self.ckpt_phase = self.curr_phase
            self.ckpt_phase_index = self.curr_phase_index
            self.ckpt_step = self.curr_step
            self.ckpt_fwk_global_time = self.fwk.fwk_global_time
            for c in list(self.my_comps.keys()):
                self.ckpt_comps.append(c)
        else:
            # we are transitioning to a new phase
            self.ckpt_phase_index += 1
            self.ckpt_phase = self.phase_list[self.ckpt_phase_index]
            self.ckpt_step = 1
            self.ckpt_fwk_global_time = self.fwk.fwk_global_time
            del self.my_comps
            self.my_comps = {}
            for n, c in list(self.all_comps.items()):
                if c.phase == self.ckpt_phase:
                    self.ckpt_comps.append(n)


    def restart_setup(self):
        """
        This is called when a restart is needed.  Current state is saved to determine when rework will be done.
        """
        if self.fwk.debug:
            print(" ##### restarting", self.fwk.fwk_global_time, self.curr_phase, self.curr_step)
        #self.num_faults += 1
        self.fwk.logEvent(self.name, None, 'restart_setup', 'restarting simulation at step %d' % self.curr_step)
        if self.state == 'work':
            # save current state so we know when we are done doing rework
            self.rework_done_step = self.curr_step
            self.rework_done_phase = self.curr_phase
            self.rework_done_phase_index = self.curr_phase_index
            self.total_lost_time += min(self.fwk.fwk_global_time - self.ckpt_fwk_global_time, self.fwk.fwk_global_time - self.last_submission_time)
        else:
            if self.fwk.debug:
                print("failure occured during rework period")
        # kill running tasks
        self.state = 'restart'
        for c in list(self.all_comps.values()):
            c.ready_for_step = 0
        for c in list(self.my_comps.values()):
            if c.retry:
                c.retry = False
                c.curr_retries = 0
            if c.using.nodes > 0:
                c.kill_task()
        del self.my_comps
        self.my_comps = {}
        #print "killed tasks"

    def restart_restore_state(self):
        """
        This method restores the state of the sim to that of the last checkpoint.
        """
        self.num_restarts += 1
        self.num_rework += 1
        self.total_restart_time += self.my_overheads['restart'].runtime
        self.start_rework_time = self.fwk.fwk_global_time
        self.curr_phase = self.ckpt_phase
        self.curr_phase_index = self.ckpt_phase_index
        self.curr_step = self.ckpt_step
        #self.total_steps = self.curr_step
        if self.fwk.debug:
            print(" ##### rework", self.fwk.fwk_global_time, self.curr_phase, self.curr_step)
        self.fwk.logEvent(self.name, None, 'restart_restore', 'restarting simulation from step %d' % self.curr_step)
        del self.my_comps
        self.my_comps = {}
        print(self.ckpt_comps)
        for c in self.ckpt_comps:
            self.my_comps.update({c:self.all_comps[c]})
            self.all_comps[c].ready_for_step = self.curr_step
            self.all_comps[c].state = "not_done"
            self.my_comps[c].ready_for_step = self.curr_step
            self.my_comps[c].state = "not_done"
        self.state = 'rework'


    def update_bookkeeping(self):
        """
        After the simulation has completed, the framework calls the method to get the accounting information from the simulation.  The component and overhead objects are queried for their accounting information.  The framework uses this information to relay it back to the user.
        """
        for c in list(self.all_comps.values()):
            #print c.name
            self.total_usage += c.total_usage
            self.total_work_time += c.total_time
            self.total_waiting_time += c.total_waiting_time
            self.num_waiting += c.num_waiting
            self.num_faults += c.num_faults
            self.num_retries += c.num_retries
            if self.mode == "normal":
                self.total_rework_time += c.total_rework_time
        if self.mode == "total_time":
            self.total_restart_time = self.restart_comp.total_restart_time
            self.total_ckpt_time = self.ckpt_comp.total_ckpt_time
            self.total_rework_time = self.rework_comp.total_rework_time
        else:
            if self.ckpt_on:
                self.total_ckpt_time = self.my_overheads['checkpoint'].total_time
            self.steps_todo = 0
            self.total_overhead = self.my_overheads['startup'].total_time + self.my_overheads['shutdown'].total_time
            self.total_restart_time = self.my_overheads['restart'].total_time
            self.total_resubmit_time = self.my_overheads['resubmit'].total_time
            self.total_launch_delay = self.my_overheads['launch_delay'].total_time
            for p in list(self.phases.values()):
                self.steps_todo += p.nsteps
            self.completed_work = self.total_steps




# end simulation object
