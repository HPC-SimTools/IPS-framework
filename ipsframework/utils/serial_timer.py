#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

import sys
from . import BeautifulSoup
import urllib.request
import urllib.error
import urllib.parse
from math import floor

PLOT = True
PLOT_MULTIPLE_INSTANCES = False   # Separate concurrent instances of the same component
PLOT_END_EDGE = False             # Plot an edge whenever a task finishes
try:
    from pylab import figure, vlines, xlabel, ylabel, title, grid, plot, plt, show
except Exception:
    PLOT = False


def plot_exec_time(plot_data, used_procs, used_proc_map, task_procs):
    import numpy as np
    figure()
    x = [float(k) for k in sorted(list(plot_data.keys()), key=float)]
    y = np.array([plot_data[k] for k in sorted(list(plot_data.keys()), key=float)])
    # plot(x, y)
    vlines(x, [0], y, colors='b')
#    l = legend()
    xlabel('Wall Time')
    ylabel('Serial Execution Time')
    title('Serial Execution Periods for IPS Simulation')
    grid(True)
    figure()
    sorted_proc_times = sorted(list(used_procs.keys()), key=float)
    x = [float(k) for k in sorted_proc_times]
    y = [used_procs[k] for k in sorted_proc_times]
    plot(x, y)
    area = 0.0
    for k in range(len(sorted_proc_times) - 1):
        area += used_procs[sorted_proc_times[k]] * \
            (float(sorted_proc_times[k + 1]) - float(sorted_proc_times[k]))
    average_util = area / (float(sorted_proc_times[-1]) - float(sorted_proc_times[0]))
#    l = legend()
    xlabel('Wall Time')
    ylabel('Processor Count')
    title('Processor Utilization')

    print('===========================')
    all_util = {}
    start_point = int(floor(x[0]))
    for index in range(1, len(x)):
        end_point = int(floor(x[index]))
        value = y[index]
        for t in range(start_point, end_point):
            all_util[t] = value
#            print t, value
        start_point = end_point
    print('===========================')

    values = [all_util[k] for k in sorted(list(all_util.keys()), key=float)]
    window = 3600
    moving_sum = sum(values[0:window])
    moving_ave = {window / 2: moving_sum / float(window)}
    for index in range(window / 2 + 1, len(values) - window / 2):
        index_in = index + int(floor(window / 2))
        index_out = index - int(floor(window / 2)) - 1
        moving_sum += (values[index_in] - values[index_out])
        moving_ave[index] = moving_sum / float(window)

    # for k in sorted(moving_ave.keys(), key = float):
    #    print k, moving_ave[k]

    # x2 = [float(k) for k in sorted(list(moving_ave.keys()), key=float)]
    # y2 = [moving_ave[k] for k in sorted(list(moving_ave.keys()), key=float)]
    # plot_label = '%.1fH Moving Ave.' % (float(window / 3600.))
    # plot(x2, y2, linewidth=2, label = plot_label)

    grid(True)
    plot([sorted_proc_times[0], sorted_proc_times[-1]], [average_util, average_util],
         linewidth=2, label='Average')
    plt.legend()

    fig = figure()
    comp_names = list(used_proc_map.keys())
    comp_name = comp_names[0]
    comp_util = used_proc_map[comp_name]
    all_times = sorted(comp_util.keys())

    print('%15s' % ('Time'), end=' ')
    for comp in comp_names:
        print('%15s' % (comp), end=' ')
    print()
    for t in all_times:
        print('%15.5f' % (t), end=' ')
        for comp in comp_names:
            print('%15d' % (used_proc_map[comp][t]), end=' ')
        print()

    print(task_procs)
    x = np.array(all_times)
    y_sum = np.array([0.0 for wall_time in all_times])
    y = {}
    ax1 = fig.add_subplot(111)

#    x0 = np.array([0.0, all_times[-1]])
#    y0 = np.array([total_procs, total_procs])
#    ax1.plot(x0, y0, linestyle = '--', linewidth = 2)
    colors = ["#CC6666", "#1DACD6", "#6E5160"]
    comp_color = {}
    for comp in comp_names:
        print('plotting for ', comp)
        data = used_proc_map[comp]
        y[comp] = np.array([data[wall_time] for wall_time in all_times])
        comp_color[comp] = colors.pop(0)
        y_plot_old = y_sum.copy()
        if (PLOT_MULTIPLE_INSTANCES):
            print(max(y[comp]), task_procs[comp], max(y[comp]) / task_procs[comp])
            max_num_comp_sims = max(y[comp]) / task_procs[comp]
            print(max_num_comp_sims + 1)
            y_inc = [0] * len(y[comp])
            for i in range(1, max_num_comp_sims + 1):
                for t in range(len(y_inc)):
                    y_inc[t] = min(y_inc[t] + task_procs[comp], y[comp][t])
                y_plot = y_inc + y_sum
                if(i == 1):
                    ax1.plot(x, y_plot, label=comp, markeredgecolor='c',
                             markerfacecolor=comp_color[comp], color='k', linewidth=0.5)
                else:
                    ax1.plot(x, y_plot, markeredgecolor='c',
                             markerfacecolor=comp_color[comp], color='k', linewidth=0.5)
                plt.fill_between(x, y_plot, y_plot_old, color=comp_color[comp], alpha=0.5)
                y_plot_old = y_plot
        else:
            y_plot = y[comp] + y_sum
            ax1.plot(x, y_plot, label=comp, markeredgecolor='c',
                     markerfacecolor=comp_color[comp], color='k', linewidth=0.5)
            plt.fill_between(x, y_plot, y_plot_old, color=comp_color[comp], alpha=0.5)

        y_sum = y_plot
    lgd = ax1.legend(numpoints=2, handletextpad=-1, ncol=3, loc='upper center', fancybox=False,
                     mode=None)  # , prop = {'size':10})
    lines = lgd.get_lines()
    lgd_texts = lgd.get_texts()
    for i in range(len(lines)):
        line = lines[i]
        comp_name = lgd_texts[i]
        fill_color = comp_color[comp_name.get_text()]
        line.set_linestyle('')
        line.set_marker('s')
        line.set_markersize(12)
        line.set_markevery(2)
        line.set_markerfacecolor(fill_color)
        line.set_alpha(0.5)
        line.set_markeredgecolor('k')
        line.set_markeredgewidth(1.5)
    plt.xlabel('Wall Time (Sec.)')
    plt.ylabel('Cores Used')
    show()


def get_task_times(url_list):
    task_data = {}
    active_tasks = {}
    used_procs = {}
    task_map = {}
    task_start_map = {}
    task_end_map = {}
    all_task_times = []
    all_comp_names = []
    task_procs = {}
    for url in url_list:
        try:
            page = urllib.request.urlopen(url)
        except Exception:
            print('Error retreiving URL ', url)
            raise
        parsed_page = BeautifulSoup.BeautifulSoup(page)
        events_table = parsed_page('table')[3]
        events = events_table('tr')[1:]
        for event in events:
            fields = event('td')
            field_values = [field.contents[0].strip() for field in fields]
            if (field_values[2] == 'IPS_TASK_END'):
                # print ' '.join(field_values)
                comment = field_values[-1]
                comp = field_values[3]
                if comp not in all_comp_names:
                    all_comp_names.append(comp)
                comment_fields = comment.split()
                raw_task_id = comment_fields[comment_fields.index('task_id') + 2]
                phys_stamp = field_values[-2]
                wall_time = field_values[-3]
                all_task_times.append((wall_time, 'END'))
                task_data[wall_time] = 'END'
                task_id = url + '|' + raw_task_id
                try:
                    new_task = task_map[task_id]
                except KeyError:
                    new_task = Task(task_id=task_id,
                                    end_time=float(wall_time),
                                    phys_time=float(phys_stamp),
                                    comp_name=comp)
                    task_map[task_id] = new_task
                else:
                    new_task.end_time = float(wall_time)
                try:
                    task_end_map[wall_time].append(task_id)
                except Exception:
                    task_end_map[wall_time] = [task_id]
                # print phys_stamp, comp_task, exec_time
            elif (field_values[2] in ['IPS_LAUNCH_TASK_POOL', 'IPS_LAUNCH_TASK']):
                comment = field_values[-1]
                comp = field_values[3]
                wall_time = field_values[-3]
                all_task_times.append((wall_time, 'START'))
                comment_fields = comment.split()
                raw_task_id = comment_fields[comment_fields.index('task_id') + 2]
                task_id = url + '|' + raw_task_id
                phys_stamp = field_values[-2]
                print(comment_fields)
                if 'mpiexec' in comment_fields:
                    dash_n_idx = comment_fields.index('-n')
                    nproc = int(comment_fields[dash_n_idx + 1])
                else:
                    try:
                        aprun = comment_fields.index('aprun')
                        nproc = int(comment_fields[aprun + 2])
                    except Exception:
                        raise
                try:
                    new_task = task_map[task_id]
                except KeyError:
                    new_task = Task(task_id=task_id,
                                    nproc=nproc,
                                    start_time=float(wall_time),
                                    phys_time=float(phys_stamp),
                                    comp_name=comp)
                    task_map[task_id] = new_task
                else:
                    new_task.nproc = nproc
                    new_task.start_time = wall_time
                    new_task.phys_time = phys_stamp
                try:
                    task_start_map[wall_time].append(task_id)
                except Exception:
                    task_start_map[wall_time] = [task_id]
                if comp not in all_comp_names:
                    all_comp_names.append(comp)
                if comp not in list(task_procs.keys()):
                    task_procs[comp] = nproc
                    print(comp, task_procs[comp])
            elif(field_values[2] == 'IPS_START'):
                wall_time = field_values[-3]
                all_task_times.append((wall_time, 'IPS_START'))
                active_tasks[wall_time] = 0

    all_task_times = sorted(all_task_times, key=lambda x: float(x[0]))

    print('wall_time, nproc_started')
    for wall_time in sorted(list(task_start_map.keys()), key=float):
        tid_list = task_start_map[wall_time]
        print(wall_time, [task_map[tid].nproc for tid in tid_list])
    print('======================================================')
    print('wall_time, nproc_ended')
    for wall_time in sorted(list(task_end_map.keys()), key=float):
        tid_list = task_end_map[wall_time]
        print(wall_time, [task_map[tid].nproc for tid in tid_list])
    print('======================================================')

    current_used_procs = 0
    active_tasks_count = 0
    used_proc_map = {}
    cur_util_map = {}
    for comp in all_comp_names:
        used_proc_map[comp] = {}
        cur_util_map[comp] = 0

    while True:
        try:
            (event_time, event) = all_task_times.pop(0)
        except IndexError:
            break
        if (event == 'START'):
            tid = task_start_map[event_time].pop(0)
            prior_walltime = '%f' % (float(event_time) - 0.00001)
            active_tasks[prior_walltime] = active_tasks_count
            used_procs[prior_walltime] = current_used_procs
            task = task_map[tid]
            active_tasks_count += 1
            current_used_procs += task.nproc

            comp_name = task.comp_name
            used_proc_per_comp = used_proc_map[comp_name]
            if float(event_time) - 0.00001 not in list(used_proc_per_comp.keys()):
                if (PLOT_END_EDGE):
                    used_proc_per_comp[float(event_time) - 0.00003] = cur_util_map[comp_name]
                    used_proc_per_comp[float(event_time) - 0.00002] = cur_util_map[comp_name]
                used_proc_per_comp[float(event_time) - 0.00001] = cur_util_map[comp_name]

            cur_util_map[comp_name] += task.nproc
            used_proc_per_comp[float(event_time)] = cur_util_map[comp_name]

            for other_comp in all_comp_names:
                if comp_name == other_comp:
                    continue
                used_proc_per_comp = used_proc_map[other_comp]
                used_proc_per_comp[float(event_time)] = cur_util_map[other_comp]
                if (PLOT_END_EDGE):
                    used_proc_per_comp[float(event_time) - 0.00003] = cur_util_map[other_comp]
                    used_proc_per_comp[float(event_time) - 0.00002] = cur_util_map[other_comp]
                used_proc_per_comp[float(event_time) - 0.00001] = cur_util_map[other_comp]

        elif (event == 'END'):
            prior_walltime = '%f' % (float(event_time) - 0.00001)
            active_tasks[prior_walltime] = active_tasks_count
            used_procs[prior_walltime] = current_used_procs
            tid = task_end_map[event_time].pop(0)
            task = task_map[tid]
            active_tasks_count -= 1
            current_used_procs -= task.nproc

            comp_name = task.comp_name
            used_proc_per_comp = used_proc_map[comp_name]
            if float(event_time) - 0.00001 not in list(used_proc_per_comp.keys()):
                if (PLOT_END_EDGE):
                    used_proc_per_comp[float(event_time) - 0.00003] = cur_util_map[comp_name]
                    used_proc_per_comp[float(event_time) - 0.00002] = 0
                    used_proc_per_comp[float(event_time) - 0.00001] = 0
                else:
                    used_proc_per_comp[float(event_time) - 0.00001] = cur_util_map[comp_name]

            cur_util_map[comp_name] -= task.nproc
            used_proc_per_comp[float(event_time)] = cur_util_map[comp_name]
            for other_comp in all_comp_names:
                if comp_name == other_comp:
                    continue
                used_proc_per_comp = used_proc_map[other_comp]
                used_proc_per_comp[float(event_time)] = cur_util_map[other_comp]
                if (PLOT_END_EDGE):
                    used_proc_per_comp[float(event_time) - 0.00003] = cur_util_map[other_comp]
                    used_proc_per_comp[float(event_time) - 0.00002] = cur_util_map[other_comp]
                used_proc_per_comp[float(event_time) - 0.00001] = cur_util_map[other_comp]

        elif (event == 'IPS_START'):
            current_used_procs = 0
            active_tasks_count = 0
        active_tasks[event_time] = active_tasks_count
        used_procs[event_time] = current_used_procs

#    print 'Wall Time,  Active Tasks,  Used Procs'
#    for wall_time in sorted(active_tasks.keys(), key = float):
#        print wall_time, active_tasks[wall_time], used_procs[wall_time]

    print('======================================================')
    print('   Task ID,     Start time,     End time')
    for tid in sorted(list(task_map.keys()), key=lambda x: float(x.split('|')[1])):
        task = task_map[tid]
        print('%10s  %10s  %10s' % (tid.split('|')[1], str(task.start_time), str(task.end_time)))

    index = 0
    serial_times = {}
    print('==============================================')
    print('Serial Times')
    print('    Start      Stop      Interval')

    sorted_walltime = sorted(list(active_tasks.keys()), key=float)
    for i in range(len(sorted_walltime)):
        if active_tasks[sorted_walltime[i]] == 0:
            try:
                index = sorted_walltime[i]
                interval = float(sorted_walltime[i + 1]) - float(sorted_walltime[i])
                if (interval > 0.1):
                    serial_times[index] = interval
                    print('%12.3f %12.3f %12.3f' %
                          (float(sorted_walltime[i]),
                           float(sorted_walltime[i + 1]), interval))
            except IndexError:
                pass
                # index += 1

    if (PLOT):
        plot_exec_time(serial_times, used_procs, used_proc_map, task_procs)


class Task:
    def __init__(self,
                 task_id=None,
                 nproc=-1,
                 start_time=-1.0,
                 end_time=-1.0,
                 phys_time=-1.0,
                 comp_name=''):
        self.task_id = task_id
        self.nproc = nproc
        self.start_time = start_time
        self.end_time = end_time
        self.phys_time = phys_time
        self.comp_name = comp_name

    pass


if __name__ == '__main__':
    get_task_times(sys.argv[1:])
    sys.exit(0)
