# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Experimentinator
----------------

by Samantha Foley, ORNL

Creates, runs, and post-processes ensembles of RUS runs.

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
    """
    Prints a summary of the flags you can use.
    """
    print('This script will run and process the results from executing an ensemble of RUS runs.')
    print('Please use the following options to specify what experiments to perform and graph:')
    print('   -i, --interleave : number of simulations that execute at the same time.')
    print('   -p, --ppn : processes per node')
    print('   -t, --trials : number of times to run each experiment')
    print('   -n, --name : name of experiment to help with identification')
    print('   -m, --minnodes : minimum number of nodes needed to run the sim(s)')
    print('   -f, --cfile : path to config file to simulate')
    print('   -j, --nodeinterval : number of nodes between allocation sizes to simulate')


class summ_dt:
    def __init__(self):
        self.val = None
        self.nodes = None
        self.index = None


class experiment_suite:
    """
    contains everything that is needed to create, run and keep track of an ensemble of rus runs.
    """

    def __init__(self):
        self.num_comps = 4  # default
        self.time_per_sim_step = 1200
        self.runtime_variance = 0
        self.interleaving = 4  # default
        self.ppn = 4  # default
        self.trials = 1  # default
        self.variance = 0  # default
        self.id = ''
        self.steps = 10  # default
        self.cfiles = list()
        self.node_interval = 16

        try:
            opts, args = getopt.getopt(
                sys.argv[1:],
                'c:s:v:i:p:t:n:k:f:m:j:z:',
                ['ncomps=', 'simtime=', 'var=', 'interleave=', 'ppn=', 'trials=', 'name=', 'steps=', 'cfile=', 'minnodes=', 'nodeinterval='],
            )
        except getopt.GetoptError as err:
            # print help information and exit:
            print(str(err))  # will print something like "option -a not recognized"
            usage()
            sys.exit(2)

        try:
            for o, a in opts:
                if o == '-c' or o == '--ncomps':
                    self.num_comps = int(a)
                elif o == '-s' or o == '--simtime':
                    self.time_per_sim_step = int(a)
                elif o == '-v' or o == '--var':
                    self.variance = int(a)
                elif o == '-i' or o == '--interleave':
                    self.interleaving = int(a)
                elif o == '-p' or o == '--ppn':
                    self.ppn = int(a)
                elif o == '-t' or o == '--trials':
                    self.trials = int(a)
                elif o == '-n' or o == '--name':
                    self.id = a
                elif o == '-k' or o == '--steps':
                    self.steps = int(a)
                elif o == '-f' or o == '--cfile':
                    self.cfiles.append(a)
                elif o == '-m' or o == '--minnodes':
                    self.minnodes = int(a)
                elif o == '-z' or o == '--concurrent_min':
                    self.concurrent_min = int(a)
                elif o == '-j' or o == '--nodeinterval':
                    self.node_interval = int(a)
        except:
            print('problems getting command line arguments')
            raise
        # print "ready to construct simulations"
        # self.perms = generate_perms(self.num_comps, self.time_per_sim_step)
        # print self.perms

    def set_up(self):
        """
        Constructs the simulation files, resource files and experiment objects as specified.
        """
        self.my_sims = dict()
        try:
            # ===================================================================
            # # create sim object
            # ===================================================================
            for s in self.cfiles:
                d, f = os.path.split(s)
                k = simulation()
                k.name = f
                k.fname = s
                self.my_sims.update({f: k})
            self.maxnodes = self.concurrent_min * self.interleaving

        except:
            print('problem setting up sim objects')
            raise

        # =======================================================================
        # # node values ranging from min # nodes to max # nodes in intervals of 16
        # =======================================================================
        node_vals = list()
        for j in range(1, self.interleaving + 1):
            node_vals.append(list(range(self.minnodes, self.concurrent_min * j + 1, self.node_interval)))

        for r in node_vals[-1]:
            fname = 'resource_files/res_' + 'n' + str(r) + '_p' + str(self.ppn)
            if not os.path.exists(fname):
                # ===============================================================
                # #need to create resource file
                # ===============================================================
                f = open(fname, 'w')
                print('machine_name = unicorn', file=f)
                print('nodes = ', r, file=f)
                print('ppn = ', self.ppn, file=f)
                print('mem_pernode = 0', file=f)
                print('disk_pernode = 0', file=f)
                f.close()

        # =======================================================================
        # # generate experiment list
        # =======================================================================
        ltm = 'logTypeMap'
        log = 'gen' + self.id
        self.my_exps = list()

        for k, v in list(self.my_sims.items()):
            for i in range(0, self.interleaving):
                for r in node_vals[i]:
                    e = experiment(v, r, self.ppn, self.trials, self.id, i + 1)
                    self.my_exps.append(e)

    def run(self):
        """
        Runs the suite of experiments and grabs their output.
        """
        for i in range(self.trials):
            for e in self.my_exps:
                try:
                    p = subprocess.Popen(e.launch_str, stdout=subprocess.PIPE, close_fds=True)
                    o = p.communicate()[0]
                    print(o)
                    # status: *Succeeded* if the simulation was able to
                    # complete, otherwise, *Failed*.
                    # seed: random number seed used for this run.
                    # total time: total time charged by the system (in other words,
                    # spent in an allocation).
                    # allocation size: number of nodes requested.
                    # CPU hrs charged: the number of *hours* charged for this run.
                    # CPU hrs used: the number of *hours* used for this run.
                    # work time: amount of time spent doing work.
                    # rework time: amount of time spend redoing work.
                    # ckpt time: amount of time spent taking check points.
                    # restart time: amount of time spent loading data from a checkpoint.
                    # launch delay time: amount of time spent delaying task relaunches.
                    # resubmit time: amount of time spent setting up the framework and
                    # simulation in a new batch allocation.
                    # overhead time: amount of time spent doing other overhead activities
                    # (for instance, simulation startup and shutdown).
                    ## ckpts: number of checkpoints taken
                    ## node failures: number of node failures that occurred over the
                    # course of the simulation.
                    ## faults: number of interrupts experienced by the application.
                    ## relaunch: number of times any task was relaunched.
                    ## restart: number of times the simulation was rolled back and
                    # restarted from a checkpoint
                    ## resubmit: number of times the framework ran out of nodes and
                    # started again in a new batch allocation from the beginning or a checkpoint.

                    s, ms, t, c, chc, chu, w, r, p, rs, ld, rb, o, nc, n, nf, nrl, ns, nb = o.split()
                    e.trials.ts[i].ts_set(t, chc, chu, float(chu) / float(chc), ms)
                except:
                    print('problems with run %s on %d nodes, trial %d' % (e.sim.name, e.nodes, i))
                    raise

    def post_analysis(self):
        """
        Analyze and graph resource usage and efficiency data.
        """
        plt.gca().set_autoscale_on(False)
        tm = strftime('%H.%M.%S', gmtime())
        dump = open('dump_plot_data' + tm, 'w')

        # =======================================================================
        # # initialize lists for gathering data
        # =======================================================================
        xn = list()
        y_t = list()
        y_c = list()
        y_u = list()
        y_e = list()

        for j in range(self.interleaving):
            xn.append(list())
            y_t.append(list())
            y_u.append(list())
            y_c.append(list())
            y_e.append(list())

        # =======================================================================
        # # initialize vars to gather max and min
        # =======================================================================
        min_effcy = summ_dt()
        max_effcy = summ_dt()
        self.my_mins = list()
        self.my_maxs = list()
        min_effcy.val = [100] * self.interleaving
        max_effcy.val = [0] * self.interleaving
        min_effcy.nodes = [0] * self.interleaving
        max_effcy.nodes = [0] * self.interleaving
        print('interleave nodes time charged used effcy', file=dump)
        for e in self.my_exps:
            i = e.interleave - 1
            e.trials.minmaxavg()
            n = e.nodes
            t = e.trials.avg.time / e.interleave
            c = e.trials.avg.cpuhrs_charged
            u = e.trials.avg.cpuhrs_used
            f = round((u / c) * 100)  # e.trials.avg.effcy
            xn[i].append(n)
            y_t[i].append(t)
            y_c[i].append(c)
            y_u[i].append(u)
            y_e[i].append(f)

            print(e.interleave, n, e.trials.avg.time, c, u, f, file=dump)

            # ===================================================================
            # # calculate min and max
            # ===================================================================
            if f < min_effcy.val[i]:
                min_effcy.val[i] = f
                min_effcy.nodes[i] = n
            if f > max_effcy.val[i]:
                max_effcy.val[i] = f
                max_effcy.nodes[i] = n

        for e in self.my_exps:
            c = e.trials.avg.cpuhrs_charged
            u = e.trials.avg.cpuhrs_used
            f = round((u / c) * 100)  # e.trials.avg.effcy
            self.minimamaxima(f, e.nodes, e.interleave, 2, e.trials.avg.time, c)

        # =======================================================================
        # # make pretty graphs
        # =======================================================================

        efficiency_axes = [self.minnodes * 4, self.maxnodes * 4, 0, 110]
        time_axes = [self.minnodes * 4, self.maxnodes * 4, 0, (y_t[0][-1] + 0.10 * y_t[0][-1]) / 1000.0]
        """
        plt.figure(1)
        for j in range(1, self.interleaving):
            plt.subplot(self.interleaving-1, 1, j)
            plt.axis(efficiency_axes)
            #plt.xlim(self.minnodes, self.maxnodes)
            #plt.ylim(0, 110)
            curr_l = 'Efficiency v. Time: Interleaving ' + str(j + 1)
            plt.plot(xn[j], y_e[0]*len(xn[j]), 'k--', label='Serial Efficiency')
            plt.plot(xn[j], y_e[j], 'k', label='Interleaved Efficiency')
            plt.xlabel('nodes')
            plt.ylabel('Efficiency')
            plt.title(curr_l)

            plt.twinx()
            plt.axis(time_axes)
            plt.plot(xn[j], y_t[0]*len(xn[j]), 'g--', label='Serial Time')
            plt.plot(xn[j], y_t[j], 'g', label='Interleaved Time')
            plt.ylabel('Time', color = 'g')

        plt.legend()
        plt.savefig("otherpic" + tm + ".pdf")
        """
        color_chars = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        efficiency_axes = [self.minnodes * 4, self.maxnodes * 4, 0, 100]
        plt.figure()
        for j in range(self.interleaving):
            plt.subplot(1, 2, 1, autoscale_on=False)
            curr_l = 'Efficiency: Interleaving ' + str(j + 1)
            if j == 0:
                for nc in range(1, len(y_e[j])):
                    plt.plot(
                        [k * 4 for k in xn[self.interleaving - 1]],
                        y_e[nc] * len(xn[self.interleaving - 1]),
                        color_chars[nc % 7] + '--',
                        label='Serial Efficiency %d cores' % (xn[j][nc]),
                    )

            else:
                plt.plot([k * 4 for k in xn[j]], y_e[j], color_chars[j % 7], label='Efficiency' + str(j + 1))
            plt.xlabel('Cores (ppn = %d)' % self.ppn)
            plt.ylabel('% Efficiency')
            # plt.title(curr_l)
            plt.axis(efficiency_axes)

            plt.subplot(1, 2, 2, autoscale_on=False)
            curr_l = 'Time: Interleaving ' + str(j + 1)
            if j == 0:
                plt.plot(
                    [k * 4 for k in xn[self.interleaving - 1]],
                    [temp_x / 1000.0 for temp_x in y_t[0] * len(xn[self.interleaving - 1])],
                    color_chars[j % 7] + '--',
                    label='1 Sim',
                )
            else:
                plt.plot([k * 4 for k in xn[j]], [temp_x / 1000.0 for temp_x in y_t[j]], color_chars[j % 7], label=str(j + 1) + ' Sims')
            plt.xlabel('Cores (ppn = %d)' % self.ppn)
            plt.ylabel('Time (1000 seconds)')
            # plt.title(curr_l)
            plt.axis(time_axes)
        plt.suptitle('Efficiency and Time versus Nodes\nfor Interleaved Simulations')
        plt.legend()
        plt.savefig('prettypic' + tm + '.pdf')

        """
        efficiency_axes = [self.minnodes*4, self.maxnodes*4, -10, 300]
        time_axes = [self.minnodes*4, self.maxnodes*4, -10, 300]
        plt.figure()
        plt.subplots_adjust(wspace = 0.3)
        for j in range(self.interleaving):
            plt.subplot(1, 2, 1, autoscale_on=False)
            curr_l = 'Efficiency: Interleaving ' + str(j + 1)
            if j == 0:
                plt.plot([k*4 for k in xn[self.interleaving-1]], [0]*len(xn[self.interleaving-1]), color_chars[j % 7]+'--', label='1 Sim')
            else:
                plt.plot([k*4 for k in xn[j]], [100 * ((y_tmp - y_e[0][0]) / y_e[0][0]) for y_tmp in y_e[j]], color_chars[j % 7], label='Efficiency'+str(j+1))
            plt.xlabel('Cores (ppn = %d)' % self.ppn)
            plt.ylabel('% Improvement: Efficiency')
            #plt.title(curr_l)
            plt.axis(efficiency_axes)

            plt.subplot(1, 2, 2, autoscale_on=False)
            curr_l = 'Time: Interleaving ' + str(j + 1)
            if j == 0:
                plt.plot([k*4 for k in xn[self.interleaving-1]], [0]*len(xn[self.interleaving-1]), color_chars[j % 7]+'--', label='1 Sim')
            else:
                plt.plot([k*4 for k in xn[j]], [100 * ((y_t[0][0] - temp_x)/y_t[0][0]) for temp_x in y_t[j]], color_chars[j % 7], label=str(j+1)+' Sims')
            plt.xlabel('Cores (ppn = %d)' % self.ppn)
            plt.ylabel('% Improvement: Time')
            #plt.title(curr_l)
            plt.axis(time_axes)
        plt.suptitle('Efficiency and Time versus Nodes\nfor Interleaved Simulations')
        plt.legend()
        plt.savefig("normalpic" + tm + ".pdf")
        """
        # =======================================================================
        # # summary of experiment
        # #   - output the names of the config files used
        # #   - the range of resource files used
        # #   - levels of interleaving
        # #   - minimum and maximum efficiency values
        # =======================================================================
        summ_file = open('summary.' + tm, 'w')
        print('Simulations: ', ', '.join(list(self.my_sims.keys())), file=summ_file)
        print('Allocation sizes: from', self.minnodes, 'to', self.maxnodes, end=' ', file=summ_file)
        print('with an interval of', self.node_interval, ', a ppn value of', self.ppn, ', and a trial count of', self.trials, file=summ_file)
        print('Minimum and Maximum Efficiency values for each interleaving level:', file=summ_file)
        for i in range(self.interleaving):
            print(
                '\t%d |\tmin: %d percent \t%d cores |\tmax: %d percent \t%d cores |'
                % (i + 1, min_effcy.val[i], min_effcy.nodes[i] * self.ppn, max_effcy.val[i], max_effcy.nodes[i] * self.ppn),
                file=summ_file,
            )

        print('============================================', file=summ_file)
        print('Local Minima:', file=summ_file)
        for m in self.my_mins:
            print(
                '# sims: %d\t efficiency: %d\t cores: %d\t time: %d\t cost: %f CPU Hours' % (m.interleave, m.effcy, m.nodes * self.ppn, m.time, m.cost),
                file=summ_file,
            )

        print('============================================', file=summ_file)
        print('Local Maxima:', file=summ_file)
        for m in self.my_maxs:
            print(
                '# sims: %d\t efficiency: %d\t cores: %d\t time: %d\t cost: %f CPU Hours' % (m.interleave, m.effcy, m.nodes * self.ppn, m.time, m.cost),
                file=summ_file,
            )

    def minimamaxima(self, effcy, nodes, interleave, neighborhood, time, cost):
        """
        determines if this value is a minima or maxima and adds it to the list
        """
        mates = list()
        # find neighbors
        for e in self.my_exps:
            if (
                (e.interleave == interleave)
                and (e.nodes >= (nodes - (neighborhood * self.node_interval)))
                and (e.nodes <= (nodes + (neighborhood * self.node_interval)))
                and not (e.nodes == nodes)
            ):
                mates.append(e)
        # print 'grrr', effcy,
        # =======================================================================
        # # is val less than all neighbors?
        # =======================================================================
        is_min = True
        for e in mates:
            c = e.trials.avg.cpuhrs_charged
            u = e.trials.avg.cpuhrs_used
            f = int((u / c) * 100)  # e.trials.avg.effcy
            # print 'grrr', 'is', effcy, ' less than', f, '?',
            if f < effcy:
                # print 'no'
                is_min = False
                break

        is_max = True
        # =======================================================================
        # # is val greater than all neighbors?
        # =======================================================================
        for e in mates:
            c = e.trials.avg.cpuhrs_charged
            u = e.trials.avg.cpuhrs_used
            f = int((u / c) * 100)  # e.trials.avg.effcy
            # print 'grrr', 'is', effcy, ' greater than', f, '?',
            if f > effcy:
                # print 'no'
                is_max = False
                break

        if is_min:
            self.my_mins.append(minmax_dt(effcy, nodes, interleave, time, cost))

        if is_max:
            self.my_maxs.append(minmax_dt(effcy, nodes, interleave, time, cost))


class minmax_dt:
    """
    (deprecated?) Container for calculating min and max.
    """

    def __init__(self, e, n, i, t, c):
        self.effcy = e
        self.nodes = n
        self.interleave = i
        self.time = t
        self.cost = c


class trial_stats:
    """
    Container for the data produced by a single experiment object over many trials.  Each trial is represented by a trial_stats object.  The methods act as operators to generate an average for the experiment.
    """

    def __init__(self):
        self.time = 0
        self.cpuhrs_charged = 0
        self.cpuhrs_used = 0
        self.effcy = 0
        self.seed = 0

    def ts_set(self, t, c, u, e, s):
        self.time = int(float(t))
        self.cpuhrs_charged = float(c)
        self.cpuhrs_used = float(u)
        self.effcy = float(e)  # (self.cpuhrs_used / self.cpuhrs_charged) * 100
        self.seed = int(s)

    def ts_copy(self, ts):
        self.time = ts.time
        self.cpuhrs_charged = ts.cpuhrs_charged
        self.cpuhrs_used = ts.cpuhrs_used
        self.effcy = ts.effcy

    def ts_accum(self, ts):
        self.time += ts.time
        self.cpuhrs_charged += ts.cpuhrs_charged
        self.cpuhrs_used += ts.cpuhrs_used
        self.effcy += self.effcy

    def ts_div(self, d):
        self.time = self.time / d
        self.cpuhrs_charged = self.cpuhrs_charged / d
        self.cpuhrs_used = self.cpuhrs_used / d
        self.effcy = self.effcy / d


class trial_tracker:
    """
    Container for the experiment that houses all of the trial_stats objects and calculates the minimum, maximum and average.
    """

    def __init__(self, t):
        self.avg = trial_stats()
        self.min = trial_stats()
        self.max = trial_stats()
        self.ts = list()
        for x in range(t):
            self.ts.append(trial_stats())

    def minmaxavg(self):  # based on time.... need to think about which metric to avg/min/max?
        """
        Minimum, maximum and average are calculated and stored in the object.  Comparison metric is total time.
        """
        a = trial_stats()
        min = trial_stats()
        max = trial_stats()
        min.ts_copy(self.ts[0])
        max.ts_copy(self.ts[0])

        for x in self.ts:
            if x.time < min.time:
                min.ts_copy(x)
            if x.time > max.time:
                max.ts_copy(x)
            a.ts_accum(x)
        a.ts_div(float(len(self.ts)))

        # =======================================================================
        # # set min, max and avg
        # =======================================================================
        self.min.ts_copy(min)
        self.max.ts_copy(max)
        self.avg.ts_copy(a)


class experiment:
    """
    Contains the information to run a series of trials for a particular RUS configuration.
    """

    def __init__(self, sim, nodes, ppn, t, tag, i):
        self.sim = sim
        self.nodes = nodes
        self.ppn = ppn
        self.trials = trial_tracker(t)
        self.tag = tag
        self.interleave = i
        self.gen_launch_str()

    def gen_launch_str(self):
        """
        Generates the launch string for the experiment.
        """
        m = '-m'  #' -m logTypeMap'
        mval = 'logTypeMap'
        c = '-c'  #' -c ' + self.sim.fname
        cval = self.sim.fname
        r = '-r'  #' -r res_n' + str(self.nodes) + '_p' + str(self.ppn)
        rval = 'resource_files/res_n' + str(self.nodes) + '_p' + str(self.ppn)
        if self.tag:
            l = ' -l '  # + self.tag
            lval = self.tag
            self.launch_str = ['python', 'rus.py', l, lval, m, mval, r, rval]
        else:
            self.launch_str = ['python', 'rus.py', m, mval, r, rval]

        for i in range(self.interleave):
            self.launch_str.append(c)
            self.launch_str.append(cval)


if __name__ == '__main__':
    my_experiments = experiment_suite()
    my_experiments.set_up()
    my_experiments.run()
    my_experiments.post_analysis()
    sys.exit(0)
