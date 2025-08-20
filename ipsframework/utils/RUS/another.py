# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import matplotlib

matplotlib.use('AGG')
import matplotlib.pyplot as plt
import os, sys

f_list = list()
for k in range(6):
    f_list.append(list())


def read_data(file_to_read, bin):
    times = list()
    cores = list()
    effcy = list()
    for k in range(6):
        cores.append(list())
        effcy.append(list())
        times.append(list())

    infile = open(file_to_read, 'r')
    lines = infile.readlines()
    for line in lines[1:]:
        i, n, rt, cpuc, cpuu, e = line.split()
        i = int(i)
        cores[i - 1].append(int(n) * 4)
        effcy[i - 1].append(float(e))
        times[i - 1].append(float(rt))
    infile.close()
    combo_data = list()
    for k in range(6):
        maxe = max(effcy[k])
        maxe_i = effcy[k].index(maxe)
        c = cores[k][maxe_i]
        t = times[k][maxe_i]
        # combo_data.append(zip(effcy[k], cores[k]))
        # combo_data.sort()
        # effcy[k], cores[k] = zip(*combo_data[k])
        # f_list[k].append({'bin':bin, 'effcy':effcy[k][0], 'cores':cores[k][0], 'times':times[k][0]})
        f_list[k].append({'bin': bin, 'effcy': maxe, 'cores': c, 'times': t})


def do_plotting(feature):
    lcolor = ['bo-', 'gs-', 'r*-', 'c+-', 'mx-', 'kd-']

    # plt.gca().set_autoscale_on(False)
    plt.figure()

    # plt.subplot(1, 3, 1, autoscale_on=False)
    for k in range(6):
        bins = list()
        effcys = list()
        for e in f_list[k]:
            bins.append(e['bin'])
            effcys.append(e['effcy'])
        plt.plot(bins, effcys, lcolor[k], label=str(k + 1))

    # plt.axis([1000, 7000, 0, 100])
    # plt.xlim([0,130])
    # plt.xlim([0,270])
    plt.xlim([0, 2200])
    plt.ylim([0, 100])
    plt.xlabel('Cores Used By NUBEAM')
    # plt.xlabel('Percent Time Used By TSC')
    # plt.xlabel('Percent Time Used By NUBEAM')
    plt.ylabel('Efficiency (%)')
    plt.legend(loc=0)
    # plt.title('Peak Efficiency for ANT Scenario: TSC Time Variation')
    # plt.title('Peak Efficiency for ANT Scenario: NUBEAM Time Variation')
    # plt.title('Peak Efficiency for TNT Scenario: NUBEAM Time Variation')
    # plt.title('Peak Efficiency for TNT Scenario: TSC Time Variation')
    # plt.title('Peak Efficiency for TNT Scenario: NUBEAM Weak Scaling')
    # plt.title('Peak Efficiency for TNT Scenario: NUBEAM Strong Scaling')
    # plt.title('Peak Efficiency for ANT Scenario: NUBEAM Weak Scaling')
    # plt.title('Peak Efficiency for ANT Scenario: NUBEAM Strong Scaling')
    plt.savefig('agg_swim3_nscale' + '.pdf')
    # plt.savefig('agg_swim3_ncores' + '.pdf')
    # plt.savefig('agg_swim4_ncores' + '.pdf')
    # plt.savefig('agg_swim4_ntime' + '.pdf')
    # plt.savefig('agg_swim3_ntime' + '.pdf')
    # plt.savefig('agg_swim4_tsctime' + '.pdf')
    # plt.savefig('agg_swim3_tsctime' + '.pdf')
    # plt.savefig('agg_swim4_new_ncores.pdf')
    # plt.savefig('agg_swim4_new_nscale.pdf')
    # plt.show()
    """
    plt.subplot(1,2,2, autoscale_on=False)
    for k in range(6):
        plt.plot(rt_list[k], ts_list[k], lcolor[k], label=str(k+1))
    minrt = min([min(l) for l in ts_list])
    maxrt = max([max(l) for l in ts_list])
    plt.xlabel('% simulation time used by nubeam')
    plt.ylabel('time per simulation (seconds)')
    plt.axis([16, 1024, minrt - .1*(maxrt-minrt), maxrt + .1*(maxrt-minrt)])
    plt.legend(loc='upper left')
    #plt.show()
    plt.savefig('agg_' + (sys.argv[1][:-4]) + '.pdf')
    """


if __name__ == '__main__':
    feature = sys.argv[1]
    for k in range(2, len(sys.argv), 2):
        read_data(sys.argv[k], int(sys.argv[k + 1]))
    do_plotting(feature)
    sys.exit(0)
