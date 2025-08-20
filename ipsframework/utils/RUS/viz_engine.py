# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Viz Engine
----------------

by Samantha Foley, ORNL

Creates tables of information about a dump file produced from run_exps.py.

This is primarily for understanding the fault tolerance characteristics of different ft strategies.

"""

import os, sys
import getopt
import random
import scipy
import numpy as np

# import matplotlib
# matplotlib.use('AGG')
import matplotlib.pyplot as plt
import subprocess
from time import gmtime, strftime


class trial:
    """
    trial class holds data from a single run of rus
    """

    def __init__(self, s):
        """
        initialize a trial object from a line of output
        """
        if s == 0:
            self.success = False
            self.ft_mode = 0
            self.fault_model = 0
            self.nodes = 0
            self.total_time = 0
            self.launch_delay_t = 0
            self.launch_delay_p = 0
            self.node_failures = 0
            self.resubmit_t = 0
            self.overhead_t = 0
            self.overhead_p = 0
            self.resubmit_p = 0
            self.restart_p = 0
            self.restart_t = 0
            self.resubmit_n = 0
            self.rework_p = 0
            self.rework_t = 0
            self.relaunch_n = 0
            self.restart_n = 0
            self.work_t = 0
            self.ckpt_t = 0
            self.work_p = 0
            self.ckpt_p = 0
            self.fault_n = 0
            self.ckpt_n = 0
            self.cost = 0
        else:
            sf, ftm, fm, tt, c, wt, rt, ct, st, ldt, bt, ot, nnf, nc, nf, nl, nr, nb, pw, pr, pc, ps, pld, pb, po = s.split()
            if sf == 'Success':
                self.success = True
            else:
                self.success = False
            self.ft_mode = ftm
            self.fault_model = fm
            self.nodes = int(c)
            self.total_time = float(tt)
            self.work_t = float(wt)
            self.rework_t = float(rt)
            self.ckpt_t = float(ct)
            self.restart_t = float(st)
            self.launch_delay_t = float(ldt)
            self.resubmit_t = float(bt)
            self.overhead_t = float(ot)
            self.node_failures = int(nnf)
            self.ckpt_n = int(nc)
            self.fault_n = int(nf)
            self.relaunch_n = int(nl)
            self.restart_n = int(nr)
            self.resubmit_n = int(nb)
            self.work_p = float(pw)
            self.rework_p = float(pr)
            self.ckpt_p = float(pc)
            self.restart_p = float(ps)
            self.resubmit_p = float(pb)
            self.launch_delay_p = float(pld)
            self.overhead_p = float(po)
            self.cost = self.total_time * self.nodes * 4

    def copy(self, t):
        self.success = t.success
        self.ft_mode = t.ft_mode
        self.fault_model = t.fault_model
        self.nodes = t.nodes
        self.cost = t.cost
        self.total_time = t.total_time
        self.work_t = t.work_t
        self.rework_t = t.rework_t
        self.ckpt_t = t.ckpt_t
        self.restart_t = t.restart_t
        self.launch_delay_t = t.launch_delay_t
        self.resubmit_t = t.resubmit_t
        self.overhead_t = t.overhead_t
        self.work_p = t.work_p
        self.rework_p = t.rework_p
        self.ckpt_p = t.ckpt_p
        self.restart_p = t.restart_p
        self.launch_delay_p = t.launch_delay_p
        self.resubmit_p = t.resubmit_p
        self.overhead_p = t.overhead_p
        self.ckpt_n = t.ckpt_n
        self.restart_n = t.restart_n
        self.relaunch_n = t.relaunch_n
        self.resubmit_n = t.resubmit_n
        self.node_failures = t.node_failures
        self.fault_n = t.fault_n

    def accum(self, t):
        self.cost += t.cost
        self.total_time += t.total_time
        self.work_t += t.work_t
        self.rework_t += t.rework_t
        self.ckpt_t += t.ckpt_t
        self.restart_t += t.restart_t
        self.launch_delay_t += t.launch_delay_t
        self.resubmit_t += t.resubmit_t
        self.overhead_t += t.overhead_t
        self.work_p += t.work_p
        self.rework_p += t.rework_p
        self.ckpt_p += t.ckpt_p
        self.restart_p += t.restart_p
        self.launch_delay_p += t.launch_delay_p
        self.resubmit_p += t.resubmit_p
        self.overhead_p += t.overhead_p
        self.ckpt_n += t.ckpt_n
        self.restart_n += t.restart_n
        self.relaunch_n += t.relaunch_n
        self.resubmit_n += t.resubmit_n
        self.node_failures += t.node_failures
        self.fault_n += t.fault_n

    def div(self, d):
        self.success = self.success / d
        self.ft_mode = self.ft_mode / d
        self.fault_model = self.fault_model / d
        self.nodes = self.nodes / d
        self.cost = self.cost / d
        self.total_time = self.total_time / d
        self.work_t = self.work_t / d
        self.rework_t = self.rework_t / d
        self.ckpt_t = self.ckpt_t / d
        self.restart_t = self.restart_t / d
        self.launch_delay_t = self.launch_delay_t / d
        self.resubmit_t = self.resubmit_t / d
        self.overhead_t = self.overhead_t / d
        self.work_p = self.work_p / d
        self.rework_p = self.rework_p / d
        self.ckpt_p = self.ckpt_p / d
        self.restart_p = self.restart_p / d
        self.launch_delay_p = self.launch_delay_p / d
        self.resubmit_p = self.resubmit_p / d
        self.overhead_p = self.overhead_p / d
        self.ckpt_n = self.ckpt_n / d
        self.restart_n = self.restart_n / d
        self.relaunch_n = self.relaunch_n / d
        self.resubmit_n = self.resubmit_n / d
        self.node_failures = self.node_failures / d
        self.fault_n = self.fault_n / d

    def print_me(self, f):
        print(
            '   Total time (hrs)   %.2f | Cost (CPU hours)  %.2f | Node Failures  %.2f | Faults  %.2f'
            % (self.total_time / 3600, self.cost / 3600, self.node_failures, self.fault_n),
            file=f,
        )
        print('           |  work  |  rework  |  ckpt  |  restart  |  relaunch  |  resubmit  |  overhead ', file=f)
        print(
            '   time    |  %.2f |  %.2f |  %.2f |  %.2f |  %.2f |  %.2f  |  %.2f'
            % (
                self.work_t / 3600,
                self.rework_t / 3600,
                self.ckpt_t / 3600,
                self.restart_t / 3600,
                self.launch_delay_t / 3600,
                self.resubmit_t / 3600,
                self.overhead_t / 3600,
            ),
            file=f,
        )
        print(
            '   percent |  %.2f |  %.2f |  %.2f |  %.2f |  %.2f |  %.2f  |  %.2f'
            % (self.work_p, self.rework_p, self.ckpt_p, self.restart_p, self.launch_delay_p, self.resubmit_p, self.overhead_p),
            file=f,
        )
        print(
            '   number  |   ---  |   ---   |  %.2f  |  %.2f  |  %.2f  |  %.2f  |  ---  ' % (self.ckpt_n, self.restart_n, self.relaunch_n, self.resubmit_n),
            file=f,
        )


# globals!!!
all_data = {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None}
modes = {
    'none': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'restart': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trncr': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trwcr_2': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trwcr_5': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trwcr_10': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trwcr_19': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trwcr_29': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'trwcr_39': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'simcr_2': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'simcr_5': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'simcr_10': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'simcr_19': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'simcr_29': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
    'simcr_39': {'all': [], 'savg': None, 'smin': None, 'smax': None, 'sstddev': None, 'favg': None, 'fmin': None, 'fmax': None, 'fstddev': None},
}

nodes = {258: [], 261: [], 268: [], 281: []}
# nodes = {1032:[], 1044:[], 1072:[], 1124:[]}
succeeded = {}
failed = {}
policy = {
    'none': 'none',
    'restart': 'restart from the beginning',
    'trncr': 'task relaunch, no C/R',
    'trwcr_2': 'task relaunch, with C/R interval=2',
    'simcr_2': 'no task relaunch, C/R interval=2',
    'trwcr_5': 'task relaunch, with C/R interval=5',
    'simcr_5': 'no task relaunch, C/R interval=5',
    'trwcr_10': 'task relaunch, with C/R interval=10',
    'simcr_10': 'no task relaunch, C/R interval=10',
    'trwcr_19': 'task relaunch, with C/R interval=19',
    'simcr_19': 'no task relaunch, C/R interval=19',
    'trwcr_29': 'task relaunch, with C/R interval=29',
    'simcr_29': 'no task relaunch, C/R interval=29',
    'trwcr_39': 'task relaunch, with C/R interval=39',
    'simcr_39': 'no task relaunch, C/R interval=39',
}


def produce_stats():
    """
    this is where we read in all of the data and produce tables describing what happened
    """
    # ------------------------------------------
    # init vars
    # ------------------------------------------

    # ------------------------------------------
    # get file name from command line
    # ------------------------------------------
    fname = sys.argv[1]
    infile = open(fname, 'r')
    suff = fname.strip('dump_plot_data')
    outfile = open('stats' + suff, 'w')

    # ------------------------------------------
    # parse contents
    # - discard header info
    # - organize by failed/success
    # - organize by fault model
    # ------------------------------------------
    for l in infile.readlines():
        l = l.strip()
        if not l[0] == '#':
            t = trial(l)
            all_data['all'].append(t)
            modes[t.ft_mode]['all'].append(t)
            nodes[t.nodes].append(t)
    # ------------------------------------------
    # - rank by time
    # ------------------------------------------
    # ------------------------------------------
    # - rank by % work
    # ------------------------------------------
    # ------------------------------------------
    # - min/max/avg trials
    # ------------------------------------------
    # ------------------------------------------
    # - generate data
    # ------------------------------------------
    # print >> outfile, '\n\nBreakdown by ft strategy (sorted by time)'
    for k, v in list(modes.items()):
        succeeded.update({k: 0})
        failed.update({k: 0})
        v['savg'] = trial(0)
        v['smin'] = trial(0)
        v['smax'] = trial(0)
        v['favg'] = trial(0)
        v['fmin'] = trial(0)
        v['fmax'] = trial(0)
        v['sstddev'] = trial(0)
        v['fstddev'] = trial(0)

        for i in v['all']:
            if i.success:
                succeeded[k] += 1
                if v['smin'].total_time == 0 or v['smin'].total_time > i.total_time:
                    v['smin'].copy(i)
                if v['smax'].total_time == 0 or v['smax'].total_time < i.total_time:
                    v['smax'].copy(i)
                v['savg'].accum(i)
            else:
                failed[k] += 1
                if v['fmin'].total_time == 0 or v['fmin'].total_time > i.total_time:
                    v['fmin'].copy(i)
                if v['fmax'].total_time == 0 or v['fmax'].total_time < i.total_time:
                    v['fmax'].copy(i)
                v['favg'].accum(i)
        if succeeded[k] > 0:
            v['savg'].div(float(succeeded[k]))

        if failed[k] > 0:
            v['favg'].div(float(failed[k]))

        calc_stddev(modes[k])

    avg_tt = {}
    avg_cost = {}
    avg_nf = {}
    avg_fn = {}
    avg_wp = {}
    avg_rln = {}
    avg_rsn = {}
    avg_rbn = {}
    # break down by allocation size
    for k, v in list(nodes.items()):
        succeeded.update({k: 0})
        failed.update({k: 0})
        s = []
        f = []
        for i in v:
            if i.success:
                s.append(i)
                succeeded[k] += 1
            else:
                f.append(i)
                failed[k] += 1
        if len(s) > 0 and len(f) > 0:
            avg_tt[k] = (sum([j.total_time for j in s]) / float(len(s)), sum([j.total_time for j in f]) / float(len(f)))
            avg_cost[k] = (sum([j.cost for j in s]) / float(len(s)), sum([j.cost for j in f]) / float(len(f)))
            avg_nf[k] = (sum([j.node_failures for j in s]) / float(len(s)), sum([j.node_failures for j in f]) / float(len(f)))
            avg_fn[k] = (sum([j.fault_n for j in s]) / float(len(s)), sum([j.fault_n for j in f]) / float(len(f)))
            avg_wp[k] = (sum([j.work_p for j in s]) / float(len(s)), sum([j.work_p for j in f]) / float(len(f)))
            avg_rln[k] = (sum([j.relaunch_n for j in s]) / float(len(s)), sum([j.relaunch_n for j in f]) / float(len(f)))
            avg_rsn[k] = (sum([j.restart_n for j in s]) / float(len(s)), sum([j.restart_n for j in f]) / float(len(f)))
            avg_rbn[k] = (sum([j.resubmit_n for j in s]) / float(len(s)), sum([j.resubmit_n for j in f]) / float(len(f)))
        elif len(f) == 0 and len(s) > 0:
            avg_tt[k] = (sum([j.total_time for j in s]) / float(len(s)), 0)
            avg_cost[k] = (sum([j.cost for j in s]) / float(len(s)), 0)
            avg_nf[k] = (sum([j.node_failures for j in s]) / float(len(s)), 0)
            avg_fn[k] = (sum([j.fault_n for j in s]) / float(len(s)), 0)
            avg_wp[k] = (sum([j.work_p for j in s]) / float(len(s)), 0)
            avg_rln[k] = (sum([j.relaunch_n for j in s]) / float(len(s)), 0)
            avg_rsn[k] = (sum([j.restart_n for j in s]) / float(len(s)), 0)
            avg_rbn[k] = (sum([j.resubmit_n for j in s]) / float(len(s)), 0)
        elif len(s) == 0 and len(f) > 0:
            avg_tt[k] = (0, sum([j.total_time for j in f]) / float(len(f)))
            avg_cost[k] = (0, sum([j.cost for j in f]) / float(len(f)))
            avg_nf[k] = (0, sum([j.node_failures for j in f]) / float(len(f)))
            avg_fn[k] = (0, sum([j.fault_n for j in f]) / float(len(f)))
            avg_wp[k] = (0, sum([j.work_p for j in f]) / float(len(f)))
            avg_rln[k] = (0, sum([j.relaunch_n for j in f]) / float(len(f)))
            avg_rsn[k] = (0, sum([j.restart_n for j in f]) / float(len(f)))
            avg_rbn[k] = (0, sum([j.resubmit_n for j in f]) / float(len(f)))
        else:
            avg_tt[k] = (0, 0)
            avg_cost[k] = (0, 0)
            avg_nf[k] = (0, 0)
            avg_fn[k] = (0, 0)
            avg_wp[k] = (0, 0)
            avg_rln[k] = (0, 0)
            avg_rsn[k] = (0, 0)
            avg_rbn[k] = (0, 0)

    # ---------------------------------------------------
    # output section
    # ---------------------------------------------------
    key_order = ['none', 'restart', 'trncr', 'simcr_39', 'simcr_19', 'simcr_10', 'simcr_5', 'simcr_2', 'trwcr_39', 'trwcr_19', 'trwcr_10', 'trwcr_5', 'trwcr_2']
    # ------------------------------------------
    # - chart prep
    # ------------------------------------------
    print(
        '\t\t| % successful | cost of success | total time | work time | rework time | ckpt time | restart time | launch delay | resubmit time | overhead time | resubmissions',
        file=outfile,
    )
    print(
        '========================================================================================================================================================',
        file=outfile,
    )

    tt = {258: {}, 261: {}, 268: {}, 281: {}}
    wt = {258: {}, 261: {}, 268: {}, 281: {}}
    rwt = {258: {}, 261: {}, 268: {}, 281: {}}
    ct = {258: {}, 261: {}, 268: {}, 281: {}}
    rst = {258: {}, 261: {}, 268: {}, 281: {}}
    rlt = {258: {}, 261: {}, 268: {}, 281: {}}
    rbt = {258: {}, 261: {}, 268: {}, 281: {}}
    ot = {258: {}, 261: {}, 268: {}, 281: {}}
    ns = {258: {}, 261: {}, 268: {}, 281: {}}
    nsb = {258: {}, 261: {}, 268: {}, 281: {}}
    cos = {258: {}, 261: {}, 268: {}, 281: {}}

    tt0 = {258: {}, 261: {}, 268: {}, 281: {}}
    wt0 = {258: {}, 261: {}, 268: {}, 281: {}}
    rwt0 = {258: {}, 261: {}, 268: {}, 281: {}}
    ct0 = {258: {}, 261: {}, 268: {}, 281: {}}
    rst0 = {258: {}, 261: {}, 268: {}, 281: {}}
    rlt0 = {258: {}, 261: {}, 268: {}, 281: {}}
    rbt0 = {258: {}, 261: {}, 268: {}, 281: {}}
    ot0 = {258: {}, 261: {}, 268: {}, 281: {}}
    ns0 = {258: {}, 261: {}, 268: {}, 281: {}}
    cos0 = {258: {}, 261: {}, 268: {}, 281: {}}

    work_cost = 2170 * 1024 * 1000  # cost in seconds of work time

    for d in [tt, wt, rwt, ct, rst, rlt, rbt, ot, ns, nsb, cos, tt0, wt0, rwt0, ct0, rst0, rlt0, rbt0, ot0, ns0, cos0]:
        for k2, v in list(d.items()):
            for k in key_order:
                v.update({k: 0})

    for k in key_order:
        for i in modes[k]['all']:
            if i.success:
                ns[i.nodes][k] += 1
                cos[i.nodes][k] += ((i.cost - work_cost) / work_cost) * 100
                tt[i.nodes][k] += i.total_time
                wt[i.nodes][k] += i.work_t
                rwt[i.nodes][k] += i.rework_t
                ct[i.nodes][k] += i.ckpt_t
                rst[i.nodes][k] += i.restart_t
                rlt[i.nodes][k] += i.launch_delay_t
                rbt[i.nodes][k] += i.resubmit_t
                ot[i.nodes][k] += i.overhead_t
                nsb[i.nodes][k] += i.resubmit_n
                if i.resubmit_n < 1:
                    ns0[i.nodes][k] += 1
                    cos0[i.nodes][k] += ((i.cost - work_cost) / work_cost) * 100
                    tt0[i.nodes][k] += i.total_time
                    wt0[i.nodes][k] += i.work_t
                    rwt0[i.nodes][k] += i.rework_t
                    ct0[i.nodes][k] += i.ckpt_t
                    rst0[i.nodes][k] += i.restart_t
                    rlt0[i.nodes][k] += i.launch_delay_t
                    rbt0[i.nodes][k] += i.resubmit_t
                    ot0[i.nodes][k] += i.overhead_t

        for k2 in [258, 261, 268, 281]:
            if ns[k2][k] > 0:
                cos[k2][k] = cos[k2][k] / ns[k2][k]
                tt[k2][k] = (tt[k2][k] / ns[k2][k]) / 3600
                wt[k2][k] = (wt[k2][k] / ns[k2][k]) / 3600
                rwt[k2][k] = (rwt[k2][k] / ns[k2][k]) / 3600
                ct[k2][k] = (ct[k2][k] / ns[k2][k]) / 3600
                rst[k2][k] = (rst[k2][k] / ns[k2][k]) / 3600
                rlt[k2][k] = (rlt[k2][k] / ns[k2][k]) / 3600
                rbt[k2][k] = (rbt[k2][k] / ns[k2][k]) / 3600
                ot[k2][k] = (ot[k2][k] / ns[k2][k]) / 3600
                nsb[k2][k] = nsb[k2][k] / float(ns[k2][k])
            if ns0[k2][k] > 0:
                cos0[k2][k] = cos0[k2][k] / ns0[k2][k]
                tt0[k2][k] = (tt0[k2][k] / ns0[k2][k]) / 3600
                wt0[k2][k] = (wt0[k2][k] / ns0[k2][k]) / 3600
                rwt0[k2][k] = (rwt0[k2][k] / ns0[k2][k]) / 3600
                ct0[k2][k] = (ct0[k2][k] / ns0[k2][k]) / 3600
                rst0[k2][k] = (rst0[k2][k] / ns0[k2][k]) / 3600
                rlt0[k2][k] = (rlt0[k2][k] / ns0[k2][k]) / 3600
                rbt0[k2][k] = (rbt0[k2][k] / ns0[k2][k]) / 3600
                ot0[k2][k] = (ot0[k2][k] / ns0[k2][k]) / 3600

            print(k, '(%d)' % k2, '\t|%13.2f' % ((ns[k2][k] / 100.0) * 100), end=' ', file=outfile)
            print('|%18.2f' % cos[k2][k], end=' ', file=outfile)
            print('|%11.2f' % tt[k2][k], end=' ', file=outfile)
            print('|%10.2f' % wt[k2][k], end=' ', file=outfile)
            print('|%12.2f' % rwt[k2][k], end=' ', file=outfile)
            print('|%10.2f' % ct[k2][k], end=' ', file=outfile)
            print('|%13.2f' % rst[k2][k], end=' ', file=outfile)
            print('|%13.2f' % rlt[k2][k], end=' ', file=outfile)
            print('|%14.2f' % rbt[k2][k], end=' ', file=outfile)
            print('|%11.2f' % ot[k2][k], end=' ', file=outfile)
            print('|%11.4f' % nsb[k2][k], file=outfile)
            # print >> outfile, ' '
            print(k, '(%d)' % k2, '\t|%13.2f' % ((ns0[k2][k] / 100.0) * 100), end=' ', file=outfile)
            print('|%18.2f' % cos0[k2][k], end=' ', file=outfile)
            print('|%11.2f' % tt0[k2][k], end=' ', file=outfile)
            print('|%10.2f' % wt0[k2][k], end=' ', file=outfile)
            print('|%12.2f' % rwt0[k2][k], end=' ', file=outfile)
            print('|%10.2f' % ct0[k2][k], end=' ', file=outfile)
            print('|%13.2f' % rst0[k2][k], end=' ', file=outfile)
            print('|%13.2f' % rlt0[k2][k], end=' ', file=outfile)
            print('|%14.2f' % rbt0[k2][k], end=' ', file=outfile)
            print('|%11.2f' % ot0[k2][k], end=' ', file=outfile)
            print('|%11.4f' % 0, file=outfile)

        print(
            '-------------------------------------------------------------------------------------------------------------------------------------------------------------',
            file=outfile,
        )

    # ------------------------------------------
    # - summarize by allocation size
    # ------------------------------------------
    print('\nAllocation size summary', file=outfile)
    print('Nodes | Success / Failures | Avg Time | Avg Cost | Avg Failures | Avg Faults | % Work | Avg relaunch | Avg Restart | Avg Resubmit', file=outfile)
    for k, v in sorted(list(avg_tt.items()), key=lambda m: m[0]):
        print(k, ':  ', succeeded[k], '/', failed[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (avg_tt[k][0] / 3600, avg_tt[k][1] / 3600), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (avg_cost[k][0] / 3600, avg_cost[k][1] / 3600), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % avg_nf[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % avg_fn[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % avg_wp[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % avg_rln[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % avg_rsn[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % avg_rbn[k], file=outfile)

    # ------------------------------------------
    # - summarize by policy
    # ------------------------------------------
    print('\nFT Policy summary', file=outfile)
    for k, v in sorted(modes.items()):
        print(k, ':  ', succeeded[k], '/', failed[k], end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].total_time / 3600, v['favg'].total_time / 3600), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].cost / 3600, v['favg'].cost / 3600), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].node_failures, v['favg'].node_failures), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].fault_n, v['favg'].fault_n), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].work_p, v['favg'].work_p), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].relaunch_n, v['favg'].relaunch_n), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].restart_n, v['favg'].restart_n), end=' ', file=outfile)
        print('  |  %.2f -- %.2f' % (v['savg'].resubmit_n, v['favg'].resubmit_n), file=outfile)

    # ------------------------------------------
    # - policy details
    # ------------------------------------------
    print('\nFT Policy Details', file=outfile)
    for k, v in list(modes.items()):
        print('\n------\nPolicy: %s -- succeeded %d / failed %d' % (policy[k], succeeded[k], failed[k]), file=outfile)
        print(' Successful Average:', file=outfile)
        v['savg'].print_me(outfile)
        print(' Successful Maximum:', file=outfile)
        v['smax'].print_me(outfile)
        print(' Successful Minimum:', file=outfile)
        v['smin'].print_me(outfile)
        print(' Successful Stddev:', file=outfile)
        v['sstddev'].print_me(outfile)

        print('\n Failed Average:', file=outfile)
        v['favg'].print_me(outfile)
        print(' Failed Maximum:', file=outfile)
        v['fmax'].print_me(outfile)
        print(' Failed Minimum:', file=outfile)
        v['fmin'].print_me(outfile)
        print(' Failed Stddev:', file=outfile)
        v['fstddev'].print_me(outfile)

    outfile.close()

    # ------------------------------------------
    # Make Bar Chart
    # ------------------------------------------
    plt.gca().set_autoscale_on(False)

    all_tt = []
    all_wt = []
    all_rwt = []
    all_ct = []
    all_rlt = []
    all_rst = []
    all_rbt = []
    all_ot = []
    all_ns = []
    all_ns0 = []
    all_c = []
    all_c0 = []
    ind = []
    for k in [258, 261, 268, 281]:
        if k == 258:
            mm = 0
        elif k == 261:
            mm = 50
        elif k == 268:
            mm = 100
        elif k == 281:
            mm = 150
        for k2 in key_order:
            if k == 268:
                all_c.append(cos[k][k2])
                all_c0.append(cos0[k][k2])
                all_tt.append(tt[k][k2])
                all_ns.append(ns[k][k2])
                all_ns0.append(ns0[k][k2])
            all_wt.append(wt[k][k2])
            all_rwt.append(rwt[k][k2])
            all_ct.append(ct[k][k2])
            all_rlt.append(rlt[k][k2])
            all_rst.append(rst[k][k2])
            all_rbt.append(rbt[k][k2])
            all_ot.append(ot[k][k2])
            ind.append(mm + key_order.index(k2) * 4)
        ind[-1] += mm

    plt.figure()
    width = 4.0  # the width of the bars: can also be len(x) sequence
    p1 = plt.bar(ind, all_wt, width, color='r')
    p2 = plt.bar(ind, all_rwt, width, color='y', bottom=all_wt)
    my_bottom = [sum(pair) for pair in zip(all_wt, all_rwt)]
    p3 = plt.bar(ind, all_ct, width, color='b', bottom=my_bottom)
    my_bottom = [sum(pair) for pair in zip(my_bottom, all_ct)]
    p4 = plt.bar(ind, all_rlt, width, color='g', bottom=my_bottom)
    my_bottom = [sum(pair) for pair in zip(my_bottom, all_rlt)]
    p5 = plt.bar(ind, all_rst, width, color='m', bottom=my_bottom)
    my_bottom = [sum(pair) for pair in zip(my_bottom, all_rst)]
    p6 = plt.bar(ind, all_rbt, width, color='c', bottom=my_bottom)
    my_bottom = [sum(pair) for pair in zip(my_bottom, all_rbt)]
    p7 = plt.bar(ind, all_ot, width, color='k', bottom=my_bottom)

    plt.ylabel('Time in Hours')
    plt.title('Average Time Spent per FT Policy')
    xtl = [k2 for k2 in key_order] + [k2 for k2 in key_order] + [k2 for k2 in key_order] + [k2 for k2 in key_order]
    plt.xticks([i + width / 2.0 for i in ind], xtl, rotation='vertical')
    # plt.yticks(np.arange(0,81,10))
    plt.legend((p1[0], p2[0], p3[0], p4[0], p5[0], p6[0], p7[0]), ('Work', 'Rework', 'Ckpt', 'Launch Delay', 'Restart', 'Resubmit', 'Overhead'))

    # plt.savefig('bar_graph1.pdf')
    plt.show()

    plt.figure()
    width = 4.0
    # none, restart, trncr, simcr39, simcr19, simcr10, simcr5, simcr2, trwcr39, trwcr19, trwcr10, trwcr5, trwcr2
    new_ind = [1, 6, 11, 16, 20, 24, 28, 32, 37, 41, 45, 49, 53]
    print(new_ind)
    print(all_tt)
    da_bars = []
    my_colors = ['k', 'y', 'b', 'g', 'g', 'g', 'g', 'g', 'm', 'm', 'm', 'm', 'm']
    for i in range(len(all_tt)):
        da_bars.append(plt.bar(new_ind[i], all_tt[i], width, color=my_colors[i]))
    # p8 = plt.bar(new_ind, all_tt, width, color='b')
    plt.ylabel('Time in Hours')
    plt.title('Average Time to Solution per FT Policy')
    plt.xticks([i + width / 2.0 for i in new_ind], key_order, rotation='vertical')
    # plt.legend(p8, 'Total Time to Solution')
    plt.hlines(602.78, 0, new_ind[-1] + 4, 'r', linewidth=2)

    # plt.savefig('bar_graph2.pdf')
    plt.show()

    # graph of success rates
    plt.figure()
    plt.subplot(1, 2, 1)
    xvals = [39, 19, 10, 5, 2]
    plt.plot(xvals, all_ns0[3:8], 'r^-', linewidth=2, label='C/R')
    # plt.plot(xvals, all_ns[3:8], 'r^--', label='C/R, with resubmissions')
    plt.plot(xvals, all_ns0[8:], 'bv-', linewidth=2, label='C/R + T/R')
    # plt.plot(xvals, all_ns[8:], 'bv--', label='T/R, with resubmissions')
    plt.axis([0, 40, 0, 40])
    plt.ylabel('% Successful')
    plt.xlabel('Checkpoint Interval (Phys. Time)')
    # plt.title('Likelihood of Success vs. FT Strategies')
    plt.xticks(xvals)
    plt.legend()

    plt.subplot(1, 2, 2)
    xvals = [39, 19, 10, 5, 2]
    plt.plot(xvals, all_c[3:8], 'r^-', linewidth=2, label='C/R')
    plt.plot(xvals, all_c[8:], 'bv-', linewidth=2, label='C/R + T/R')
    plt.xlabel('Checkpoint Interval (Phys. Time)')
    plt.ylabel('FT Cost (%)')
    plt.axis([0, 40, 0, 45])
    # plt.title('Cost of Completion')
    plt.xticks(xvals)
    plt.legend()

    plt.savefig('success_cost' + suff + '.pdf')
    plt.show()


# end produce_stats


def calc_stddev(k):
    stt = []  # total time
    sc = []  # cost
    swt = []
    srwt = []
    sct = []
    srst = []
    srbt = []
    sldt = []
    sot = []
    swp = []
    srwp = []
    scp = []
    srsp = []
    srbp = []
    sldp = []
    sop = []
    scn = []
    srsn = []
    srbn = []
    srln = []
    snf = []
    sfn = []

    ftt = []  # total time
    fc = []  # cost
    fwt = []
    frwt = []
    fct = []
    frst = []
    frbt = []
    fldt = []
    fot = []
    fwp = []
    frwp = []
    fcp = []
    frsp = []
    frbp = []
    fldp = []
    fop = []
    fcn = []
    frsn = []
    frbn = []
    frln = []
    fnf = []
    ffn = []

    for i in k['all']:
        if i.success:
            stt.append(i.total_time)
            sc.append(i.cost)
            swt.append(i.work_t)
            srwt.append(i.rework_t)
            srst.append(i.restart_t)
            srbt.append(i.resubmit_t)
            sct.append(i.ckpt_t)
            sldt.append(i.launch_delay_t)
            sot.append(i.overhead_t)
            swp.append(i.work_p)
            srwp.append(i.rework_p)
            srsp.append(i.restart_p)
            srbp.append(i.resubmit_p)
            scp.append(i.ckpt_p)
            sldp.append(i.launch_delay_p)
            sop.append(i.overhead_p)
            srsn.append(i.restart_n)
            srbn.append(i.resubmit_n)
            scn.append(i.ckpt_n)
            srln.append(i.relaunch_n)
            sfn.append(i.fault_n)
            snf.append(i.node_failures)
        else:
            ftt.append(i.total_time)
            fc.append(i.cost)
            fwt.append(i.work_t)
            frwt.append(i.rework_t)
            frst.append(i.restart_t)
            frbt.append(i.resubmit_t)
            fct.append(i.ckpt_t)
            fldt.append(i.launch_delay_t)
            fot.append(i.overhead_t)
            fwp.append(i.work_p)
            frwp.append(i.rework_p)
            frsp.append(i.restart_p)
            frbp.append(i.resubmit_p)
            fcp.append(i.ckpt_p)
            fldp.append(i.launch_delay_p)
            fop.append(i.overhead_p)
            frsn.append(i.restart_n)
            frbn.append(i.resubmit_n)
            fcn.append(i.ckpt_n)
            frln.append(i.relaunch_n)
            ffn.append(i.fault_n)
            fnf.append(i.node_failures)
    k['sstddev'].total_time = scipy.std(stt)
    k['sstddev'].cost = scipy.std(sc)
    k['sstddev'].work_t = scipy.std(swt)
    k['sstddev'].rework_t = scipy.std(srwt)
    k['sstddev'].ckpt_t = scipy.std(sct)
    k['sstddev'].restart_t = scipy.std(srst)
    k['sstddev'].launch_delay_t = scipy.std(sldt)
    k['sstddev'].resubmit_t = scipy.std(srbt)
    k['sstddev'].overhead_t = scipy.std(sot)
    k['sstddev'].work_p = scipy.std(swp)
    k['sstddev'].rework_p = scipy.std(srwp)
    k['sstddev'].ckpt_p = scipy.std(scp)
    k['sstddev'].restart_p = scipy.std(srsp)
    k['sstddev'].launch_delay_p = scipy.std(sldp)
    k['sstddev'].resumbit_p = scipy.std(srbp)
    k['sstddev'].overhead_p = scipy.std(sop)
    k['sstddev'].ckpt_n = scipy.std(scn)
    k['sstddev'].restart_n = scipy.std(srsn)
    k['sstddev'].relaunch_n = scipy.std(srln)
    k['sstddev'].resubmit_n = scipy.std(srbn)
    k['sstddev'].fault_n = scipy.std(sfn)
    k['sstddev'].node_failures = scipy.std(snf)

    k['fstddev'].total_time = scipy.std(ftt)
    k['fstddev'].cost = scipy.std(fc)
    k['fstddev'].work_t = scipy.std(fwt)
    k['fstddev'].rework_t = scipy.std(frwt)
    k['fstddev'].ckpt_t = scipy.std(fct)
    k['fstddev'].restart_t = scipy.std(frst)
    k['fstddev'].launch_delay_t = scipy.std(fldt)
    k['fstddev'].resubmit_t = scipy.std(frbt)
    k['fstddev'].overhead_t = scipy.std(fot)
    k['fstddev'].work_p = scipy.std(fwp)
    k['fstddev'].rework_p = scipy.std(frwp)
    k['fstddev'].ckpt_p = scipy.std(fcp)
    k['fstddev'].restart_p = scipy.std(frsp)
    k['fstddev'].launch_delay_p = scipy.std(fldp)
    k['fstddev'].resumbit_p = scipy.std(frbp)
    k['fstddev'].overhead_p = scipy.std(fop)
    k['fstddev'].ckpt_n = scipy.std(fcn)
    k['fstddev'].restart_n = scipy.std(frsn)
    k['fstddev'].relaunch_n = scipy.std(frln)
    k['fstddev'].resubmit_n = scipy.std(frbn)
    k['fstddev'].fault_n = scipy.std(ffn)
    k['fstddev'].node_failures = scipy.std(fnf)


def make_graphs():
    """
    this is where we will produce some pretty graphs of things
    """
    pass


# end make_graphs

if __name__ == '__main__':
    produce_stats()
    # make_graphs()
    sys.exit(0)
