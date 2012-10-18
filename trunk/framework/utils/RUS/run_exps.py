#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
"""
Run Experiements
----------------

by Samantha Foley, ORNL

Creates, runs, and post-processes runs of RUS to model fault tolerant capabilities.

"""
import os, sys
import getopt
import random
import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt
import subprocess
from time import gmtime, strftime

def usage():
    print "This script will run and process the results from executing an ensemble of RUS runs."
    print "Please use the following options to specify what experiments to perform and graph:"
    print "   -i, --interleave : number of simulations that execute at the same time."
    print "   -p, --ppn : processes per node"
    print "   -t, --trials : number of times to run each experiment"
    print "   -n, --name : name of experiment to help with identification"
    print "   -m, --minnodes : minimum number of nodes needed to run the sim(s)"
    print "   -f, --cfile : path to config file to simulate"
    print "   -j, --nodeinterval : number of nodes between allocation sizes to simulate"



class experiment_suite():
    """
    contains everything that is needed to create, run and keep track of an ensemble of rus runs.
    """
    def __init__(self):
        self.trials = 1 # default
        self.id = ''
        self.cfiles = list()
        self.rfiles = list()
        self.tag = 'hhh'
        try:
            opts, args = getopt.getopt(sys.argv[1:], 't:c:r:n:', ['trials=', 'config_list=', 'res_list=', 'name='])
        except getopt.GetoptError, err:
            # print help information and exit:
            print str(err) # will print something like "option -a not recognized"
            usage()
            sys.exit(2)

        try:
            for o,a in opts:
                if o == '-c' or o == '--config_list':
                    cfname = a
                elif o == '-r' or o == '--res_list':
                    rfname = a
                elif o == '-t' or o == '--trials':
                    self.trials = int(a)
                elif o == '-n' or o == '--name':
                    self.tag = a
        except:
            print 'problems getting command line arguments'
            raise

        try:
            cf = open(cfname, 'r')
            for c in cf.readlines():
                self.cfiles.append(c.strip())
            cf.close()
            rf = open(rfname, 'r')
            for r in rf.readlines():
                self.rfiles.append(r.strip())
            rf.close()
        except:
            print 'problems with opening list files'
            raise

    def set_up(self):
        """
        Create list of *experiment* objects.
        """
        #=======================================================================
        # # generate experiment list
        #=======================================================================
        ltm = 'logTypeMap'
        log = 'gen' + self.id
        self.my_exps = list()

        for c in self.cfiles:
            #------------------
            # determine ft mode
            #------------------
            if c.find('_cr_') > 0:
                ft_mode = 'simcr'
            elif c.find('_tr_') > 0:
                ft_mode = 'task relaunch with cr'
            elif c.find('_trncr') > 0:
                ft_mode = 'task relaunch no cr'
            elif c.find('_none') > 0:
                ft_mode = 'none'
            elif c.find('_restart') > 0:
                ft_mode = 'restart'

            #------------------------
            # determine ckpt interval
            #------------------------
            if c.find('_i29') > 0:
                interval = 29
            elif c.find('_i2') > 0:
                interval = 2
            elif c.find('_i5') > 0:
                interval = 5
            elif c.find('_i10') > 0:
                interval = 10
            elif c.find('_i19') > 0:
                interval = 19
            elif c.find('_i39') > 0:
                interval = 39
            else:
                interval = 0
            for r in self.rfiles:
                #-----------------------
                # determine fault model
                #-----------------------
                if r.find('_p4_e') > 0:
                    fault_model = 'exponential'
                elif r.find('_p4_w7') > 0:
                    fault_model = 'weibull 0.7'
                elif r.find('_p4_w8') > 0:
                    fault_model = 'weibull 0.8'
                e = experiment(c, r, ft_mode, interval, fault_model, self.trials, self.tag)
                self.my_exps.append(e)

    def run(self):
        """
        Runs and captures output from the list of experiments.
        """
        os.chdir('/Users/f2y/Documents/ORNL/repos/ips_trunk/framework/utils/RUS')
        for i in range(self.trials):
            for e in self.my_exps:
                try:
                    p = subprocess.Popen(e.launch_str, stdout=subprocess.PIPE, close_fds=True)
                    o = p.communicate()[0]
                    print o
                    s, ms, t, c, chc, chu, w, r, p, rs, ld, rb, o, nc, n, nf, nrl, ns, nb = o.split()
                    if s == 'Success':
                        e.trials.ts[i].ts_set(True, t, c, w, r, p, rs, ld, rb, o, n, ns, nb, nf, nrl, nc)
                    else:
                        e.trials.ts[i].ts_set(False, t, c, w, r, p, rs, ld, rb, o, n, ns, nb, nf, nrl, nc)
                except:
                    e.trials.ts[i].ts_set(False, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                    print 'launch str:', e.launch_str
                    print 'problems with execution of %s using %s, trial %d' % (e.config, e.res, i)
                    #raise

    def post_analysis(self):
        """
        output data to a file to be parsed separately for viz work
        """
        tm = strftime("%H.%M.%S", gmtime())
        dump = open('dump_plot_data' + tm, 'w')
        print >> dump, "# this file contains the output from %d trials of the following resource and config files" % self.trials
        print >> dump, "# ---------------------------------------- "
        print >> dump, "# Config Files:"
        for c in self.cfiles:
            print >> dump, '#', c
        print >> dump, "# ---------------------------------------- "
        print >> dump, "# Resource Files:"
        for r in self.rfiles:
            print >> dump, '#', r
        print >> dump, "# ---------------------------------------- "
        print >> dump, '# success/failure | fault model | ft_strategy | total time | allocation size | work | rework | ckpt | restart | launch delay | resubmit | overhead | # node failures | # ckpts | # fault | # relaunch | # restart | # resubmit | % work | % rework | % ckpt | % overhead'
        print >> dump, "# ---------------------------------------- "
        for e in self.my_exps:
            e.trials.minmaxavg()
            e.print_to_file(dump)

class trial_stats():
    """
    container class for trial statistics.
    """
    def __init__(self):
        self.total_time = 0
        self.cores = 0
        self.work_time = 0
        self.rework_time = 0
        self.ckpt_time = 0
        self.restart_time = 0
        self.launch_delay = 0
        self.resubmit_time = 0
        self.overhead_time = 0
        self.num_resubmit = 0
        self.num_restart = 0
        self.num_faults = 0
        self.num_node_failures = 0
        self.num_relaunch = 0
        self.num_ckpts = 0
        self.cpuhrs_charged = 0
        self.percent_work = 0
        self.percent_rework = 0
        self.percent_ckpt = 0
        self.percent_restart = 0
        self.percent_resubmit = 0
        self.percent_launch_delay = 0
        self.percent_overhead = 0
        self.success = False

    def ts_set(self, s, t, c, w, r, p, rs, ld, rb, o, n, ns, nb, nf, nrl, nc):
        """
        set ``self`` to the values listed:
         - s = success
         - t = total time
         - c = *nodes*
         - w = work time
         - r = rework time
         - p = checkpoint time
         - rs = restart time
         - ld = launch delay
         - rb = resubmit time
         - o = overhead time
         - n = # node failures
         - ns = # restarts
         - nb = # resubmits
         - nf = # faults
         - nrl = # relaunches
         - nc = # checkpoints
        """
        self.success = s
        self.total_time = float(t)
        self.cores = int(c)
        self.work_time = float(w)
        self.rework_time = float(r)
        self.ckpt_time = float(p)
        self.restart_time = float(rs)
        self.launch_delay = float(ld)
        self.resubmit_time = float(rb)
        self.overhead_time = float(o)
        self.num_resubmit = int(nb)
        self.num_restart = int(ns)
        self.num_faults = int(nf)
        self.num_node_failures = int(n)
        self.num_relaunch = int(nrl)
        self.num_ckpts = int(nc)
        self.cpuhrs_charged = self.total_time * self.cores * 4
        if t > 0:
            self.percent_work = self.work_time / self.total_time * 100
            self.percent_rework = self.rework_time / self.total_time * 100
            self.percent_ckpt = self.ckpt_time / self.total_time * 100
            self.percent_restart = self.restart_time / self.total_time * 100
            self.percent_launch_delay = self.launch_delay / self.total_time * 100
            self.percent_resubmit = self.resubmit_time / self.total_time * 100
            self.percent_overhead = self.overhead_time / self.total_time * 100

    def ts_copy(self, ts):
        """
        copy the values of ``ts`` to ``self``
        """
        self.total_time = ts.total_time
        self.work_time = ts.work_time
        self.rework_time = ts.rework_time
        self.ckpt_time = ts.ckpt_time
        self.restart_time = ts.restart_time
        self.launch_delay = ts.launch_delay
        self.resubmit_time = ts.resubmit_time
        self.overhead_time = ts.overhead_time
        self.num_resubmit = ts.num_resubmit
        self.num_restart = ts.num_restart
        self.num_faults = ts.num_faults
        self.num_node_failures = ts.num_node_failures
        self.num_relaunch = ts.num_relaunch
        self.num_ckpts = ts.num_ckpts
        self.cpuhrs_charged = ts.cpuhrs_charged
        self.percent_work = ts.percent_work
        self.percent_rework = ts.percent_rework
        self.percent_ckpt = ts.percent_ckpt
        self.percent_restart = ts.percent_restart
        self.percent_launch_delay = ts.percent_launch_delay
        self.percent_resubmit = ts.percent_resubmit
        self.percent_overhead = ts.percent_overhead


    def ts_accum(self, ts):
        """
        add the values of ``ts`` to ``self``
        """
        if ts.success:
            self.total_time += ts.total_time
            self.work_time += ts.work_time
            self.rework_time += ts.rework_time
            self.ckpt_time += ts.ckpt_time
            self.restart_time += ts.restart_time
            self.launch_delay += ts.launch_delay
            self.resubmit_time += ts.resubmit_time
            self.overhead_time += ts.overhead_time
            self.num_resubmit += ts.num_resubmit
            self.num_restart += ts.num_restart
            self.num_faults += ts.num_faults
            self.num_node_failures += ts.num_node_failures
            self.num_relaunch += ts.num_relaunch
            self.num_ckpts += ts.num_ckpts
            self.cpuhrs_charged += ts.cpuhrs_charged
            self.percent_work += ts.percent_work
            self.percent_rework += ts.percent_rework
            self.percent_ckpt += ts.percent_ckpt
            self.percent_restart += ts.percent_restart
            self.percent_launch_delay += ts.percent_launch_delay
            self.percent_resubmit += ts.percent_resubmit
            self.percent_overhead += ts.percent_overhead

    def ts_div(self, f):
        """
        divide the values of ``self`` by ``f``
        """
        if f > 0:
            self.total_time = self.total_time / f
            self.work_time = self.work_time / f
            self.rework_time = self.rework_time / f
            self.ckpt_time = self.ckpt_time / f
            self.restart_time = self.restart_time / f
            self.launch_delay = self.launch_delay / f
            self.resubmit_time = self.resubmit_time / f
            self.overhead_time = self.overhead_time / f
            self.num_resubmit = self.num_resubmit / f
            self.num_restart = self.num_restart / f
            self.num_faults = self.num_faults / f
            self.num_node_failures = self.num_node_failures / f
            self.num_relaunch = self.num_relaunch / f
            self.num_ckpts = self.num_ckpts / f
            self.cpuhrs_charged = self.cpuhrs_charged / f
            self.percent_work = self.percent_work / f
            self.percent_rework = self.percent_rework / f
            self.percent_ckpt = self.percent_ckpt / f
            self.percent_restart = self.percent_restart / f
            self.percent_launch_delay = self.percent_launch_delay / f
            self.percent_resubmit = self.percent_resubmit / f
            self.percent_overhead = self.percent_overhead / f
        else:
            self.total_time = 0
            self.cores = 0
            self.work_time = 0
            self.rework_time = 0
            self.ckpt_time = 0
            self.restart_time = 0
            self.launch_delay = 0
            self.resubmit_time = 0
            self.overhead_time = 0
            self.num_resubmit = 0
            self.num_restart = 0
            self.num_faults = 0
            self.num_node_failures = 0
            self.num_relaunch = 0
            self.num_ckpts = 0
            self.cpuhrs_charged = 0
            self.percent_work = 0
            self.percent_rework = 0
            self.percent_ckpt = 0
            self.percent_restart = 0
            self.percent_resubmit = 0
            self.percent_launch_delay = 0
            self.percent_overhead = 0
            self.success = False

class trial_tracker():
    """
    keeps track of all the trials for a particular experiment variation (distinct combination of config files, resource files and command line options)
    """
    def __init__(self, t):
        """
        create a new trial_tracker object with ``t`` trials
        """
        self.avg = trial_stats()
        self.min = trial_stats()
        self.max = trial_stats()
        self.ts = list()
        for x in range(t):
            self.ts.append(trial_stats())

    def minmaxavg(self):  # based on time.... need to think about which metric to avg/min/max?
        """
        calculates the min, max and avg over the trials
        """
        a = trial_stats()
        min = trial_stats()
        max = trial_stats()
        min.ts_copy(self.ts[0])
        max.ts_copy(self.ts[0])

        for x in self.ts:
            if x.cpuhrs_charged < min.cpuhrs_charged:
                min.ts_copy(x)
            if x.cpuhrs_charged > max.cpuhrs_charged:
                max.ts_copy(x)
            a.ts_accum(x)
        sts = 0
        for x in self.ts:
            if x.success:
                sts += 1
        a.ts_div(float(sts))

        #=======================================================================
        # # set min, max and avg
        #=======================================================================
        self.min.ts_copy(min)
        self.max.ts_copy(max)
        self.avg.ts_copy(a)

class experiment():
    def __init__(self, cf, rf, mode, interval, model, t, tag):
        """
        create a new experiment
         - cf = config file name
         - rf = resource file name
         - mode = fault tolerance mode
         - interval = checkpoint interval for C/R FT modes
         - t = # of trials
         - tag = identifier for the log file
        """
        self.config = cf
        self.res = rf
        self.ft_mode = mode
        self.ckpt_interval = interval
        self.fault_model = model
        self.tag = tag
        self.trials = trial_tracker(t)
        self.gen_launch_str()



    def gen_launch_str(self):
        """
        constructs the command to launch the experiment
        """
        c = '-c'  #' -c ' + self.sim.fname
        cval = self.config
        r = '-r' #' -r res_n' + str(self.nodes) + '_p' + str(self.ppn)
        rval = self.res
        l = '-l' #+ self.tag
        lval = self.tag
        f = '-f'
        b = '-b'
        self.launch_str = ['python', 'rus.py', l, lval, r, rval, c, cval, f, b]
        #self.launch_str = ['python', 'rus.py', l, lval, r, rval, c, cval]

    def print_to_file(self, fhandle):
        '''
        Prints the experiment's data to ``fhandle`` prettily.
        '''
        header = ''
        #---------------------------------------
        # ft mode
        #---------------------------------------
        if self.ft_mode == 'none':
            header += 'none '
        if self.ft_mode == 'restart':
            header += 'restart '
        elif self.ft_mode == 'task relaunch with cr':
            header += 'trwcr_' + str(self.ckpt_interval) + ' '
        elif self.ft_mode == 'simcr':
            header += 'simcr_' + str(self.ckpt_interval) + ' '
        elif self.ft_mode == 'task relaunch no cr':
            header += 'trncr '
        #---------------------------------------
        # fault model
        #---------------------------------------
        if self.fault_model == 'exponential':
            header += 'exponential '
        elif self.fault_model == 'weibull 0.7':
            header += 'weibull_0.7 '
        elif self.fault_model == 'weibull 0.8':
            header += 'weibull_0.8 '
        for t in self.trials.ts:
            #---------------------------------------
            # success or failure
            #---------------------------------------
            if t.success:
                print >> fhandle, 'Success ',
            else:
                print >> fhandle, 'Failed ',
            #---------------------------------------
            # the rest of the data
            #---------------------------------------
            print >> fhandle, header, t.total_time, t.cores,
            print >> fhandle, t.work_time, t.rework_time, t.ckpt_time, t.restart_time, t.launch_delay, t.resubmit_time, t.overhead_time,
            print >> fhandle, t.num_node_failures, t.num_ckpts, t.num_faults, t.num_relaunch, t.num_restart, t.num_resubmit,
            print >> fhandle, t.percent_work, t.percent_rework, t.percent_ckpt, t.percent_restart, t.percent_launch_delay, t.percent_resubmit, t.percent_overhead

if __name__ == "__main__":
    my_experiments = experiment_suite()
    my_experiments.set_up()
    my_experiments.run()
    my_experiments.post_analysis()
    sys.exit(0)
