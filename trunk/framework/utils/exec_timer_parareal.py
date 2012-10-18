#! /usr/bin/env python
#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
# -*- coding: utf-8 -*-

import sys
import BeautifulSoup
import urllib2
import numpy as np
import math

PLOT = True
try:
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.contour import ContourSet

    #from pylab import *
except:
    PLOT = False


def plot_exec_time(task_time_map, converge, energy):
    time_fig = plt.figure(1)
    count_fig = plt.figure(2)
    converge_fig = plt.figure(3)
    time_plot = time_fig.add_subplot(111)
    count_plot = count_fig.add_subplot(111)
    converge_plot = converge_fig.add_subplot(111)
    markers = ['s', '*', '+', 'o', '1', '2', '3', '4']
    min_count = 1000
    max_count = -1
    for (comp_name, time_map) in task_time_map.items():
        x = [float(k) for k in sorted(time_map.keys(), key = float)]
        y_low = []
        y_high = []
        y_mean = []
        y_error = []
        count = []
        for k in sorted(time_map.keys(), key = float):
            y_mean.append(time_map[k][2])
            y_low.append(y_mean[-1] - time_map[k][0])
            y_high.append(time_map[k][1] - y_mean[-1])
            #y_error.append((time_map[k][0], time_map[k][1]))
            count.append(len(time_map[k][3]))

        y_error = [y_low, y_high]
        cur_marker = markers.pop(0)
        norm = sum(y_mean) / len(y_mean)
        y_mean = np.array(y_mean) / norm
        y_error = np.array(y_error) / norm
        str_norm = '%2.1f' % norm
        my_label = comp_name + ' mean ' + str_norm + ' s'
        time_plot.errorbar(x, y_mean, yerr = y_error, marker = cur_marker,
                           capsize=4, elinewidth =2, label = my_label)
        count_plot.plot(x, count, label = comp_name, marker=cur_marker)
        min_count = min([min_count, min(count)])
        max_count = max([max_count, max(count)])
    plt.figure(1)
    l = plt.legend()
    xticks = np.linspace(0, max(x), 5)
    xticks_str = ['%d' % (t) for t in xticks]
#    plt.xticks([int(f) for f in x])
    #print xticks, xticks_str
    #plt.xticks(xticks, xticks_str)
    plt.xlabel('Iteration')
    plt.ylabel('Normalized Task execution Time')
    plt.title('Execution Time Summary')
    plt.grid(True)
    plt.figure(2)
    l = plt.legend()
    #plt.xticks([int(f) for f in x])
    #plt.xticks(xticks, xticks_str)
    #print xticks_str
    #yticks = range(min_count - 1, max_count + 1)
    #plt.yticks(yticks)
    #yticks = np.linspace(min_count - 1, max_count + 1, 5)
    #yticks_str =['%d' % (t) for t in yticks]
    #plt.yticks(yticks, yticks_str)
    #print yticks_str
    plt.xlabel('Iteration')
    plt.ylabel('Task Count')
    plt.title('Parareal Tasks Count')
    plt.grid(True)

    if (len(converge) > 0):
        plt.figure(3)
        max_slice = -1
        max_iteration = -1
        for (iteration, slice) in converge.keys():
            if iteration > max_iteration:
                max_iteration = iteration
            if (slice > max_slice):
                max_slice = slice
        max_slice += 1
        max_iteration += 1
        #print max_iteration, max_slice
        iterations = np.linspace(1, max_iteration, max_iteration)
        slices = np.linspace(1, max_slice, max_slice)
        #print iterations, slices
        print [len(iterations), len(slices), len(iterations), len(slices)]
        convergence = np.ma.array(np.zeros([len(iterations), len(slices)]),
                            mask = np.ones((len(iterations), len(slices))))
        X = np.ma.array(np.zeros([len(iterations) + 1, len(slices) + 1]))
        Y = np.ma.array(np.zeros([len(iterations) + 1, len(slices) + 1]))
        X1 = np.zeros(len(iterations) + 1)
        Y1 = np.zeros(len(slices) + 1)
        Z1 = np.ones([len(slices) + 1, len(iterations) + 1])
        for i in range(len(X1)):
            X1[i] = i
        for i in range(len(Y1)):
            Y1[i] = i



        for ((iteration, slice), value) in sorted(converge.iteritems()):
            print iteration, slice, '%.3e' % (value)
            convergence[iteration, slice] = value
            convergence.mask[iteration, slice] = False
            X[iteration, slice] = X[iteration, slice + 1] = iteration - 0.5
            Y[iteration, slice] = Y[iteration + 1 , slice] = slice - 0.5
            #X[iteration, slice + 1] = iteration - 0.5
            Y[iteration, slice + 1] = Y[iteration + 1, slice + 1] = slice + 0.5
            X[iteration + 1, slice] = X[iteration + 1, slice + 1] = iteration + 0.5
            #Y[iteration + 1 , slice] = slice - 0.5
            #X[iteration + 1, slice + 1] = iteration + 0.5
            #Y[iteration + 1, slice + 1] = slice + 0.5

        # print iterations
        # print slices
        # find minimum value not equal to zero
        value_min = 1000.0
        for ((iteration, slice), value) in sorted(converge.iteritems()):

            if value > 0.0 and value < value_min:
                value_min = value
                #print 'min = ', value_min

        # set zeros to value min
        for ((iteration, slice), value) in sorted(converge.iteritems()):
            if value < value_min:
                #print 'changed ', value
                convergence[iteration, slice] = value_min
                #print ' to ', value_min
        #print convergence
        plt.ylabel('Slice')
        plt.xlabel('Iteration')
        plt.title('Slice Convergence Error')
       #plt.xticks([int(s) for s in slices])
        #plt.yticks([int(i) for i in iterations])
        #print 'min of converge = ', convergence.min()
        #print 'converge = ', convergence
        p = plt.pcolor(X.transpose(), Y.transpose(), convergence.transpose(),
                norm = LogNorm())
        tol_level = [1.5e-6]
        #CS = plt.contour(X1, Y1, Z1, levels = tol_level)

        cb = plt.colorbar(spacing='proportional', format='%.1e')
        #cb.add_line(CS)
        cb.ax.set_ylabel('Error')

    if energy:
        max_iter_map = {}
        final_energy = {}
        for (iter, slice), value in energy.iteritems():
            try:
                max_iter_map[slice] = max(max_iter_map[slice], iter)
            except KeyError:
                max_iter_map[slice] = iter
            finally:
                final_energy[slice] = energy[max_iter_map[slice], slice]
        values = [final_energy[slice] for slice in sorted(final_energy.keys())]

        plt.figure(4)
        plt.xlabel('Slice')
        plt.ylabel('Energy')
        plt.title('Energy Solution')
        plt.plot(values)
    plt.show()


def get_task_times(url_list):
    task_time_map = {}
    all_phys_stamps = set()
    converge = {}
    energy = {}
    total_energy = 0.0
    for url in url_list:
        try:
            page = urllib2.urlopen(url)
        except:
            print 'Error retreiving URL ', url
            raise
        parsed_page = BeautifulSoup.BeautifulSoup(page)
        events_table = parsed_page('table')[3]
        events = events_table('tr')[1:]
        phys_stamp_map = {}
#        print dir(events)
#        print events.reverse()
        events.reverse()
        for event in events:
            fields = event('td')
            field_values = [field.contents[0].strip() for field in fields]
            comp_task = field_values[3]
            comment = field_values[-1]
            phys_stamp_portal = field_values[-2]
            if (field_values[2] == u'IPS_LAUNCH_TASK' or field_values[2] == u'IPS_LAUNCH_TASK_POOL'):
                comment_lst = comment.split()
                task_id = comment_lst[comment_lst.index('task_id')+ 2]
                try:
                    tag = comment_lst[comment_lst.index('Tag')+ 2]
                except ValueError :
                    if field_values[2] == u'IPS_LAUNCH_TASK':
                        try:
                            (phys_stamp, slice) = comment.split()[-1].split('.')
                        except ValueError:
                            (phys_stamp, slice) = comment.split()[-2].split('.')
                    else:
                        try:
                            (phys_stamp, slice) = comment.split()[-5].split('.')
                        except ValueError:
                            (phys_stamp, slice) = comment.split()[-6].split('.')
                else:
                    (phys_stamp, slice) = tag.split('.')

                #(phys_stamp, slice) = identifier.split('.')
                #print phys_stamp, identifier, comment.split()[-2]
                if float(phys_stamp_portal) > 0.0:
                    phys_stamp = phys_stamp_portal
                phys_stamp_map[task_id] = (phys_stamp, slice)
            elif (field_values[2] == u'IPS_TASK_END'):
                task_id = comment.split()[2]
                (phys_stamp, slice) = phys_stamp_map[task_id]
                #print ' '.join(field_values)
                exec_time = comment.split()[-2]
                print '%s.%s  %10s  %s' % (phys_stamp, slice, task_id, exec_time)
                try:
                    comp_task_map = task_time_map[comp_task]
                except KeyError:
                    comp_task_map = {}
                    task_time_map[comp_task] = comp_task_map
                try:
                    (low, high, mean, values) = comp_task_map[phys_stamp]
                except KeyError:
                    (low, high, mean, values) = (2000000.0, 0.0, 0.0, [])
                exec_time = float(exec_time)
                if (exec_time < low):
                    low = exec_time
                if (exec_time > high):
                    high = exec_time
                count = len(values)
                new_mean = (mean * count + exec_time) / (count + 1.0)
                values.append(exec_time)
                comp_task_map[phys_stamp] = (low, high, new_mean, values)
                all_phys_stamps.add(phys_stamp)
            elif (field_values[2] == u'converge_out'):
                entries = comment.split()
                iteration = int(entries[0])
                slice = int(entries[1])
                conv_error = float(entries[2])
                try:
                    energy_value = float(entries[3])
                except IndexError :
                    energy_value = 0.0
                converge[iteration, slice] = conv_error
                energy[iteration, slice] = energy_value
                total_energy += energy_value

    print 'Phys_stamp',
    for comp in task_time_map.keys():
        for suffix in ['_count', '_low', '_high', '_mean']:
            print ',   ', comp+suffix,
    print

    for phys_stamp in sorted(all_phys_stamps, key = float):
        print phys_stamp,
        for comp_map in task_time_map.values():
            #print comp_map
            try:
                (low, high, mean, values) = comp_map[phys_stamp]
                print ',   ', len(values), ',', low, ',', high, ',', mean,
            except KeyError:
                print ',   ,    ,    ,     ,    ,'
        print

    if (PLOT):
        if (total_energy > 0.0):
            plot_exec_time(task_time_map, converge, energy)
        else:
            plot_exec_time(task_time_map, converge, None)

if __name__ == '__main__':
    get_task_times(sys.argv[1:])
    sys.exit(0)
