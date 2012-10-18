#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
'''
Resource Usage Simulator (RUS)
------------------------------

by Samantha Foley, Indiana University
3/4/2010

This RUS simulates the resource usage of a MCMD application as described
by the input files.  It is a tool to help users and researchers determine
how IPS runs behave in different situations.
'''

import sys, os
import getopt
from configobj import ConfigObj
from time import gmtime, strftime, asctime, time
from resource_manager import resource_mgr
from simulation import simulation
from component import component
from overhead import overhead
#from fault_events import generate_events, trigger
import subprocess
#from random import shuffle
import random
#import argparse # <----- this only works in python 2.7

comment_symbol = '%' # % in matlab, # in python, // in c/c++, ! in fortran
random_values = open("random_values", "w")

class framework():
    """
    The framework mimics the IPS framework in that it sets up and manages
    the constituent simulations, but it also manages the passage of time,
    the injection of faults, and produces output about the state of the
    simulation over time, and the cumulative usage information at the end
    of the simulation.
    """
    def __init__(self):
        self.simulation_tsteps_completed = 0
        self.simulations = list()
        self.beginning_of_time = strftime("%d_%b_%Y-%H.%M.%S", gmtime())
        self.today, self.now = self.beginning_of_time.split('-') # puts the date in self.today and the time in self.now
        self.log_types = {}
        self.curr_time = 0
        self.fwk_global_time = 0
        self.comment_symbol = '#'
        self.total_usage = 0
        self.total_rework = 0
        self.total_faults = 0
        self.usage = usage_stats()
        self.debug = False
        self.generate_viz = False
        self.failure_events = list()
        self.failures_on = False
        self.resubmit_on = False
        self.node_failures = 0
        #------------------------------------
        # get command-line arguments
        #------------------------------------
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'r:m:c:l:s:vdfb', ['resource=','config=','mapfile=','log=','seed=','produce_viz', 'debug', 'failures_on', 'resubmit_on'])
        except getopt.GetoptError, err:
            # print help information and exit:
            print str(err) # will print something like "option -a not recognized"
            usage()
            sys.exit(2)

        self.lfname = 'log'
        self.rlfname = 'log.readable'
        self.ltm = 'logTypeMap'
        cfname = ''
        self.config_files = list()

        try:
            for o,a in opts:
                #print o, a
                if o == '-m' or o == '--mapfile':
                    self.ltm = a
                elif o == '-c' or o == '--config':
                    self.config_files.append(a)
                elif o == '-l' or o == '--log':
                    self.lfname = a
                    self.rlfname = a + '.readable'
                elif o == '-r' or o == '--resource':
                    self.resource_file = a
                elif o == '-s' or o =='--seed':
                    self.myseed = int(a)
                elif o == '-v' or o == '--produce_viz':
                    self.generate_viz = True
                elif o == '-d' or o == '--debug':
                    self.debug = True
                elif o == '-f' or o == '--failures_on':
                    self.failures_on = True
                elif o == '-b' or o == '--resubmit_on':
                    self.resubmit_on = True
        except:
            print 'problems getting the command line args'
            raise
        self.my_rand = random.Random()
        try:
            self.my_rand.seed(self.myseed)
        except:
            self.myseed = int(time())
            self.my_rand.seed(self.myseed)


        #-----------------------------------------
        #   construct log files
        #-----------------------------------------
        try:
            self.create_logfiles()
        except:
            print "problems creating log files"
            raise

        #-----------------------------------------
        #   set up resource manager
        #-----------------------------------------
        try:
            self.RM = resource_mgr(self, self.resource_file)
            self.allocation_size = self.RM.nodes
        except:
            print "problems initializing the resource manager"
            raise

        #-----------------------------------------
        #    parse configuration
        #-----------------------------------------
        try:
            self.parse_config(self.config_files)
        except:
            print "problems reading config file"
            raise

        #-----------------------------------------
        #   sim and comp maps
        #-----------------------------------------
        try:
            self.setup_logfiles()
        except:
            print "problems setting up sim, comp and log type maps"
            raise

        #----------------------------------------
        #   check data
        #----------------------------------------
        if self.debug:
            for s in self.simulations:
                for c in s.my_comps.values():
                    print c.name

        #----------------------------------------
        #   set up failures
        #----------------------------------------
        if self.mtbf > 0 and self.failures_on:
            self.failure_times = list()
            if self.failure_mode == "sandia":
                for n in range(100):
                    self.failure_times.append(self.generate_event())
            else:
                for n in range(self.RM.nodes):
                    self.failure_times.append(self.generate_event())
            self.failure_times.sort()
            if self.debug:
                print 'die die die times!!!'
                print self.failure_times
                print '------'
            self.next_fe = self.find_next_fe()



    def generate_event(self):
        """
        generates a list of times when failures will occur based on mtbf
        (in seconds) specified in the resource config file, one for each
        node since each node is treated independently of the others.
        the list is then sorted.

        Note: does not account for the fact that the job was not started at the
        beginning of the hardware's lifespan.
        """
        if self.distribution == 'weibull':
            v = round(random.weibullvariate(self.mtbf, self.shape))
        elif self.distribution == 'exponential':
            v = round(random.expovariate(1.0/self.mtbf))
        else:
            return None
        random_values.write("%f\n" % v)
        return v


    def trigger(self):
        """
        this function is called when a node failure happens.  It then calls
        on the resource manager to pick a node to fail, and determines if a
        task is killed.  If a task is killed, that task's state changes to failed.
        """
        self.node_failures += 1
        to_kill = self.RM.failed_node()
        if to_kill:
            to_kill.state = "failed"
        else:
            if self.debug:
                print 'failure killed an unoccupied node'
        self.logEvent(None, None, 'node_failure', 'fault killed a node')




    def create_logfiles(self):
        """
        this function will create the logging file, ``rlogFile``.
        """

        try:
            os.mkdir(self.today)
        except:
            pass
        t = self.now
        head, rtail = os.path.split(self.resource_file)
        #self.lfname = self.today + '/' + self.lfname + '.' + t
        self.rlfname = self.today + '/' + self.rlfname + '.' + t

        #self.logFile = open(self.lfname, 'w')
        self.rlogFile = open(self.rlfname, 'w')


    def setup_logfiles(self):
        """
        set up the front matter for the logging files, and construct and record maps
        """
        #----------------------------------------
        # read logTypes into dictionary
        #----------------------------------------
        self.logTypeMap = open(self.ltm, 'r')
        logInfo = self.logTypeMap.readlines()
        for line in logInfo:
            if line:
                a = line.split()
                self.log_types.update({a[0]:int(a[1])})
        self.logTypeMap.close()

        #----------------------------------------
        # create simulation and component maps
        #----------------------------------------
        self.sim_map = dict()
        self.comp_map = dict()
        scount = 1
        ccount = 1
        self.sim_map.update({'None':0})
        for s in self.simulations:
            self.sim_map.update({s.name:scount})
            self.comp_map.update({s.name + '_' + 'None':0})
            for c in s.my_comps.values():
                self.comp_map.update({s.name + '_' + c.name:ccount})
                ccount = ccount + 1
            scount = scount + 1

        #----------------------------------------
        # write out simulation and component maps
        #----------------------------------------
        """
        for c in self.config_files:
            head, tail = os.path.split(c)
            map_file = open('sim_map' + tail, 'w')
            print >> map_file, 'simulation map:'
            for k,v in self.sim_map.items():
                print >> map_file, k, v
            print >> map_file, 'component map:'
            for k,v in self.comp_map.items():
                print >> map_file, k, v
            map_file.close()
        """
        #----------------------------------------
        # write some header info
        #----------------------------------------

        allocated, total = self.RM.get_curr_usage()
        #print >> self.logFile, comment_symbol, 'The following data is associated with the run executed at', self.beginning_of_time
        print >> self.rlogFile, comment_symbol, 'The following data is associated with the run executed at', self.beginning_of_time
        #print >> self.logFile, comment_symbol, 'On host', os.uname()[1], 'with configuration files:' #self.config_file, self.resource_file
        print >> self.rlogFile, comment_symbol, 'On host', os.uname()[1], 'with configuration files:' #self.config_file, self.resource_file
        for c in self.config_files:
            #print >> self.logFile, comment_symbol, c
            print >> self.rlogFile, comment_symbol, c
        #print >> self.logFile, comment_symbol, self.resource_file
        print >> self.rlogFile, comment_symbol, self.resource_file
        #print >> self.logFile, comment_symbol, '================================================================='
        print >> self.rlogFile, comment_symbol, '================================================================='
        self.logEvent(None, None, 'start_sim', "starting simulation")

    #-----------------------------------------------------------------------------------------------------
    #   logging functions:
    #     <global time> <sim> <component> <event type> <allocated nodes> <total nodes> <comment symbol> <comment>
    #         fwk         (------ caller -------)          (--------- RM --------)           fwk            caller
    #-----------------------------------------------------------------------------------------------------

    def logEvent(self, sim, comp, ltype, msg):
        """
        This function is used by various entities to record that an event has happened to the log file(s).  The output is in the form::

        #-----------------------------------------------------------------------------------------------------
        #   logging functions:
        #     <global time> <sim> <component> <event type> <allocated nodes> <total nodes> <comment symbol> <comment>
        #         fwk         (------ caller -------)          (--------- RM --------)           fwk         caller
        #-----------------------------------------------------------------------------------------------------

        """

        allocated, total = self.RM.get_curr_usage()
        if total > 0:
            percent = 100 * (allocated / (float(total)))
        else:
            percent = 0
        if not sim:
            s = 'None'
        else:
            s = sim
        if not comp:
            c = 'None'
        else:
            c = comp

        self.usage.add_stat(self.fwk_global_time, allocated, total, ltype)
        if s == 'None' and c == 'None':
            #print >> self.logFile, self.fwk_global_time, 0, 0, self.log_types[ltype], allocated, total, self.comment_symbol, msg
            print >> self.rlogFile, self.fwk_global_time, 'fwk', '---' , ltype, percent, '%  ', allocated, total, self.comment_symbol, msg
        elif c == 'None':
            #print >> self.logFile, self.fwk_global_time, self.sim_map[s], self.comp_map[s + '_' + c], self.log_types[ltype], percent, '%  ',allocated, total, self.comment_symbol, msg
            print >> self.rlogFile, self.fwk_global_time, sim, '---', ltype, percent, '%  ',allocated, total, self.comment_symbol, msg
        else:
            #print >> self.logFile, self.fwk_global_time, self.sim_map[s], self.comp_map[s + '_' + c], self.log_types[ltype], percent, '%  ', allocated, total, self.comment_symbol, msg
            print >> self.rlogFile, self.fwk_global_time, sim, comp, ltype, percent, '%  ', allocated, total, self.comment_symbol, msg


    def parse_config(self, conf_files):
        """
        for each configuration file in conf_files, the simulation definition sections are detected, and simulation objects created.  Further parsing happens in the simulation object, and its sub-objects.
        """
        for conf_file in conf_files:
            try:
                config = ConfigObj(conf_file, file_error=True, interpolation='template')
            except IOError, (ex):
                print 'Error opening/finding config file %s' % conf_file
                print 'ConfigObj error message: ', ex
                raise
            except SyntaxError, (ex):
                print 'Syntax problem in config file %s' % conf_file
                print 'ConfigObj error message: ', ex
                raise

            try:
                sims = config['simulation']
                if not isinstance(sims, list):
                    sims = [sims]
                for s in sims:
                    self.simulations.append(simulation(config[s], self, len(self.simulations)))
                self.description = config['description']
            except:
                print 'problem parsing simulations'
                raise

    def go(self):
        """
        This is the main loop of the simulation.  While there are simulations that are not done, components are "run", and the next update time is found.
        """
        sims = self.simulations
        done_sims = list()
        self.fwk_global_time = 0
        self.status = 'Success'
        running = []
        to_run = []
        #--------------------------------------------
        #  execute simulations
        #--------------------------------------------

        for s in sims:
            to_run.extend(s.get_ready_comps())

        while sims:
            min_update_time = 0
            running = []
            #print 'top of the loop'
            #--------------------------------------------
            # get running comps
            #--------------------------------------------

            for s in sims:
                running.extend(s.get_running_comps())

            #--------------------------------------------
            # run ready comps
            #--------------------------------------------

            for c in to_run:
                c.run()
                if c.state == "running":
                    running.append(c)

            for c in running:
                try:
                    to_run.remove(c)
                except:
                    pass

            if self.debug:
                print 'to_run:', [(k.phase, k.name, k.ready_for_step) for k in to_run]
                print 'running:', [(k.phase, k.name, k.ready_for_step) for k in running]
                print 'active nodes:', self.RM.active
                print 'total nodes:', self.RM.nodes
                print
            #--------------------------------------------
            # find update time
            #--------------------------------------------

            try:
                min_update_time = min([((c.start_exec_time + c.curr_exec_time) - self.fwk_global_time) for c in running])
            except:
                #self.logFile.close()
                #self.rlogFile.close()
                #subprocess.call(['rm', self.rlfname])
                self.logEvent(None, None, 'failed_sim', 'ran out of nodes to service task requests')
                #raise
                if self.resubmit_on:
                    # need to resubmit the whole set of sims (really just assuming there is one sim)
                    to_run = []
                    running = []
                    try:
                        for s in sims:
                            s.resubmit_setup()
                    except:
                        # exceeded resubmit limit
                        if self.debug:
                            print "exceeded resubmit limit?? look at log file %s" % self.rlfname
                        self.status = 'Failed'
                        break
                    self.RM.resubmit()
                    # new nodes need new failure times
                    if self.mtbf > 0 and self.failures_on:
                        del self.failure_times
                        self.failure_times = list()
                        if self.failure_mode == "sandia":
                            for n in range(100):
                                self.failure_times.append(self.generate_event() + self.fwk_global_time)
                        else:
                            for n in range(self.RM.nodes):
                                self.failure_times.append(self.generate_event() + self.fwk_global_time)
                        self.failure_times.sort()
                        self.next_fe = self.find_next_fe()
                    # bookkeeping????
                    # framework stuff???
                    #continue  # go back to beginning of the loop
                else:
                    #print 'not enough nodes to run tasks -- %d' % self.RM.nodes
                    self.status = 'Failed'
                    break  # break out of loop
            else:
                if self.failures_on and (self.next_fe) < (self.fwk_global_time + min_update_time):
                    min_update_time = self.next_fe - self.fwk_global_time
                    while min_update_time < 0:
                        # we need to consume and inflict all faliures that may have happened during overhead periods
                        self.trigger()
                        self.next_fe = self.find_next_fe()
                        min_update_time = self.next_fe - self.fwk_global_time
                    self.fwk_global_time += min_update_time
                    self.last_fe = self.fwk_global_time
                    self.trigger()
                    self.next_fe = self.find_next_fe()
                else:
                    self.fwk_global_time += min_update_time
                if self.debug:
                    print 'new time:', self.fwk_global_time



            #--------------------------------------------
            # update all with update time
            #--------------------------------------------
            for s in sims:
                finished_comps, nctr = s.sync(min_update_time)
                self.logEvent(None, None, 'blah', '** syncing **')
                # add next comps to run to to_run list
                for c in nctr:
                    to_run.append(c)
                if s.is_done:
                    done_sims.append(s)
                    sims.remove(s)

        # end main loop
        work_t = 0
        rework_t = 0
        ckpt_t = 0
        overhead_t = 0
        launch_delay_t = 0
        resubmit_t = 0
        restart_t = 0
        nresubmit = 0
        nfault = 0
        nrelaunch = 0
        nrestart = 0
        nckpts = 0
        # stats from successful sims
        for s in done_sims:
            s.update_bookkeeping()
            self.total_usage += s.total_usage
            work_t += s.total_work_time
            rework_t += s.total_rework_time
            ckpt_t += s.total_ckpt_time
            overhead_t += s.total_overhead
            restart_t += s.total_restart_time
            resubmit_t += s.total_resubmit_time
            launch_delay_t += s.total_launch_delay
            nresubmit += s.resubmissions
            nfault += s.num_faults
            nrelaunch += s.num_retries
            nrestart += s.num_restarts
            nckpts += s.num_ckpts
            if s.completed_work < s.steps_todo:
                #print s.completed_work, s.steps_todo
                self.status = 'Failed'
            if self.debug:
                print  "Simulation report for %s" % s.name
                if s.mode == "total_time":
                    print  "Work completed:", s.completed_work, "(", float(s.completed_work)/self.fwk_global_time * 100,"%)"
                else:
                    print  "Steps completed:", s.completed_work, "(", float(s.completed_work)/s.steps_todo * 100,"%)"
                    print  "Total productive work time:", s.total_work_time, "(", float(s.total_work_time)/self.fwk_global_time * 100, "%)"
                print  "Total checkpoint time:", s.total_ckpt_time, "(", float(s.total_ckpt_time)/self.fwk_global_time * 100,"%)"
                print  "Total rework time:", s.total_rework_time, "(", float(s.total_rework_time)/self.fwk_global_time * 100,"%)"
                print  "Total other overhead time:", s.total_overhead, "(", float(s.total_overhead)/self.fwk_global_time *100, "%)"
                print  "Total restart time:", s.total_restart_time, "(", float(s.total_restart_time)/self.fwk_global_time * 100,"%)"
                print  "Total resubmit time:", s.total_resubmit_time, "(", float(s.total_resubmit_time)/self.fwk_global_time * 100,"%)"
                print  "Total launch delay time:", s.total_launch_delay, "(", float(s.total_launch_delay)/self.fwk_global_time * 100,"%)"
                print  "Total waiting time:", s.total_waiting_time, "(", float(s.total_waiting_time)/self.fwk_global_time * 100,"%)"
                print  "Total faults:", s.num_faults
                print  "Total retries:", s.num_retries
                print  "Total resubmissions:", s.resubmissions
                print  "Number of waiting periods:", s.num_waiting
                print  "Number of checkpoints:", s.num_ckpts
                print  "Number of work segments:", s.num_work
                print  "Number of rework segments:", s.num_rework
                print  "Number of restart segments:", s.num_restarts
        # stats from failed sims
        for s in sims:
            if self.debug:
                print ' killing simulation from rus because it did not finish'
            s.kill()
            s.update_bookkeeping()
            #print 's still in sims'
            self.status = 'Failed'
            self.total_usage += s.total_usage
            work_t += s.total_work_time
            rework_t += s.total_rework_time
            ckpt_t += s.total_ckpt_time
            overhead_t += s.total_overhead
            restart_t += s.total_restart_time
            resubmit_t += s.total_resubmit_time
            launch_delay_t += s.total_launch_delay
            nresubmit += s.resubmissions
            nfault += s.num_faults
            nrelaunch += s.num_retries
            nrestart += s.num_restarts
            nckpts += s.num_ckpts
            if self.debug:
                print  "Simulation report for %s" % s.name
                if s.mode == 'total_time':
                    print  "Work completed:", s.completed_work, "(", float(s.completed_work)/self.fwk_global_time * 100,"%)"
                else:
                    print  "Steps completed:", s.completed_work, "(", float(s.completed_work)/s.steps_todo * 100,"%)"
                    print  "Total productive work time:", s.total_work_time, "(", float(s.total_work_time)/self.fwk_global_time * 100, "%)"
                print  "Total checkpoint time:", s.total_ckpt_time, "(", float(s.total_ckpt_time)/self.fwk_global_time * 100,"%)"
                print  "Total rework time:", s.total_rework_time, "(", float(s.total_rework_time)/self.fwk_global_time * 100,"%)"
                print  "Total restart time:", s.total_restart_time, "(", float(s.total_restart_time)/self.fwk_global_time * 100,"%)"
                print  "Total other overhead time:", s.total_overhead, "(", float(s.total_overhead)/self.fwk_global_time *100, "%)"
                print  "Total restart time:", s.total_restart_time, "(", float(s.total_restart_time)/self.fwk_global_time * 100,"%)"
                print  "Total resubmit time:", s.total_resubmit_time, "(", float(s.total_resubmit_time)/self.fwk_global_time * 100,"%)"
                print  "Total launch delay time:", s.total_launch_delay, "(", float(s.total_launch_delay)/self.fwk_global_time * 100,"%)"
                print  "Total waiting time:", s.total_waiting_time, "(", float(s.total_waiting_time)/self.fwk_global_time * 100,"%)"
                print  "Total faults:", s.num_faults
                print  "Total retries:", s.num_retries
                print  "Total resubmissions:", s.resubmissions
                print  "Number of waiting periods:", s.num_waiting
                print  "Number of checkpoints:", s.num_ckpts
                print  "Number of work segments:", s.num_work
                print  "Number of rework segments:", s.num_rework
                print  "Number of restart segments:", s.num_restarts
        if self.status == 'Failed':
            self.logEvent(None, None, 'failed_sim', 'ran out of nodes to service task requests')
        else:
            self.logEvent(None, None, 'end_sim', "end of simulation")
        confs = "config files: " + self.config_files[0]
        for c in self.config_files[1:]:
            confs = confs + ", " + c
        confs = confs + " -- "
        #h, conf = os.path.split(self.config_file)
        h, res = os.path.split(self.resource_file)
        cpuhrs_charged = (self.allocation_size * self.RM.ppn * self.fwk_global_time) / 3600.0
        cpuhrs_used = self.total_usage / 3600.0
        efficiency = cpuhrs_used / cpuhrs_charged
        if self.debug:
            # print >> self.rlogFile,  the config file name, nodes, ppn, total time, CPU hours
            print confs,  self.RM.nodes, 'nodes,', self.RM.ppn, 'ppn,' , self.fwk_global_time, 'seconds,', (self.RM.nodes * self.RM.ppn * self.fwk_global_time) / 3600.0, 'CPU hours, ', self.simulation_tsteps_completed, 'simulation timesteps completed'
            if self.failures_on:
                # not sure if we should use fwk_global_time for percent rework calculation
                print >> self.rlogFile,  self.total_faults, 'failures,', self.total_rework, 'total rework,', 100 * (self.total_rework / float(self.fwk_global_time)), 'percent rework'
        #print self.fwk_global_time, cpuhrs_charged, cpuhrs_used, efficiency

        #----------------------------------
        #  output for experiment manager
        #----------------------------------
        print self.status, self.myseed, self.fwk_global_time, self.allocation_size, cpuhrs_charged, cpuhrs_used,
        print work_t, rework_t, ckpt_t, restart_t, launch_delay_t, resubmit_t, overhead_t,
        print nckpts, self.node_failures, nfault, nrelaunch, nrestart, nresubmit

        if self.generate_viz:
            self.crunch()

    def find_next_fe(self):
        """
        If failures are turned on, the next failure time is returned.
        """
        if self.failures_on == False:
            return None
        else:
            new_fe = self.generate_event() + self.fwk_global_time
            #print " >>> newly added fault time", new_fe, " -  curr time:", self.fwk_global_time
            self.failure_times.append(new_fe)
            self.failure_times.sort()
            ret_val = self.failure_times[0]
            self.failure_times.remove(ret_val)
            return ret_val


    def crunch(self):
        """
        uses maptplotlib to graph the usage over time                                                                                  """
        #import matplotlib
        #matplotlib.use('AGG')
        import matplotlib.pyplot as plt
        fe_t = list()
        fe_nt = list()
        fe_nu = list()
        fe_p = list()
        fe_t1 = list()
        fe_nt1 = list()
        fe_nu1 = list()
        fe_p1 = list()

        for i in xrange(len(self.usage.times)):
            if self.usage.events[i] == 'failed_task':
                fe_t.append(self.usage.times[i])
            elif self.usage.events[i] == 'node_failure':
                fe_t1.append(self.usage.times[i])
                fe_nt1.append(self.usage.n_total[i])
                fe_nu1.append(self.usage.n_used[i])
                fe_p1.append(self.usage.percent_used[i])

        if fe_t:
            j = 0
            for k in xrange(len(fe_t1)):
                if fe_t[j] == fe_t1[k]:
                    fe_nt.append(fe_nt1[k])
                    fe_nu.append(fe_nu1[k])
                    fe_p.append(fe_p1[k])
                    j += 1
                    if j >= len(fe_t):
                        break


        print 'fe_t', fe_t
        print 'fe_nu', fe_nu


        plt.figure()
        plt.plot(self.usage.times[1:], self.usage.percent_used[:(len(self.usage.percent_used) - 1)], 'r')
        plt.ylim([0, 110])
        plt.ylabel('Percent resources in use')
        plt.xlabel('Wall clock time (seconds)')
        plt.savefig('usage_graph1-' + self.now + '.pdf', format='PDF')

        plt.figure()
        plt.plot(self.usage.times[1:], self.usage.percent_used[:(len(self.usage.percent_used) - 1)], 'r')
        plt.plot(fe_t1, [100]*len(fe_t1), 'co')
        plt.plot(fe_t, fe_p, 'kx')
        plt.ylim([0, 110])
        plt.ylabel('Percent resources in use')
        plt.xlabel('Wall clock time (seconds)')
        plt.savefig('usage_graph2-' + self.now + '.pdf', format='PDF')

        plt.figure()
        plt.plot(self.usage.times[1:], self.usage.n_total[:(len(self.usage.n_total) - 1)], 'g')
        plt.plot(self.usage.times[1:], self.usage.n_used[:(len(self.usage.n_used) - 1)], 'r')
        plt.plot(fe_t1, fe_nt1, 'co')
        plt.plot(fe_t, fe_nu, 'kx')
        plt.xlabel('Wall clock time (seconds)')
        plt.ylabel('Resources in use')
        plt.ylim([0, 1.1*max(self.usage.n_total)])

        #plt.show()
        plt.savefig('usage_graph3-' + self.now + '.pdf', format='PDF')


# end of framework

class usage_stats():
    """
    a class to manage the usage stats for creating plots.
    """
    def __init__(self):
        self.times = list()
        self.n_used = list()
        self.n_total = list()
        self.events = list()
        self.percent_used = list()

    def add_stat(self, time, used, total, event):
        if total == 0:
            p = 0.0
        else:
            p = 100 * (float(used) / total)
        if not len(self.times):
            self.times.append(time)
            self.n_used.append(used)
            self.n_total.append(total)
            self.events.append(event)
            self.percent_used.append(p)
        elif time == self.times[-1] and used == self.n_used[-1] and total == self.n_total[-1]:
            return
        else:
            self.times.append(time)
            self.n_used.append(used)
            self.n_total.append(total)
            self.events.append(event)
            self.percent_used.append(p)
            self.times.append(time)
            self.n_used.append(used)
            self.n_total.append(total)
            self.events.append(event)
            self.percent_used.append(p)

def usage():
    """
    Prints a message about the input parameters to the script.
    """
    print "This script will simulate resource usage over time of a simulation."
    print "Please use the following options:"
    print "   -c, --config : file containing component information"
    print "   -m, --mapfile : file containing valid states and an explanation of what they mean"
    print "   -l, --log : log file location, default is log.<config file name>_<num procs>"
    print "   -r, --resource : file containing resource info"

if __name__ == "__main__":
    my_fwk = framework()
    my_fwk.go()
    sys.exit(0)

"""
random thoughts

think about using sets (as they are unordered)

logging resource data:
 - toplevel log can have framework and simulation resource usage
 - simulation log can have simulation and component resource usage
 - component log can have component resource usage with more detailed event information
"""
