#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import numpy as np
from matplotlib import pyplot as plt
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print 'Format: util_viz.py <sim_log_file> [--save fmt]'
        sys.exit(1)
    fname = sys.argv[1]
    comp_names = []
    task_procs = {}
    all_events = {}
    total_procs = 0
    for event_text in open(fname).readlines():
        if event_text[0] == '%':
            continue
        try:
            event, comment = event_text.rstrip().rsplit('#')
        except ValueError:
            print event_text,  event_text.rstrip().rsplit('#')
            continue
        try:
            (wall_time_s, sim, comp, state, util, d1, d2, d3) = event.split()
        except ValueError:
            print event.split()
        wall_time = float(wall_time_s)
        if (state == 'start_sim'):
            total_procs = int(d3) * 4
        if state == 'start_task':
            try:
                nproc = task_procs[comp]
            except KeyError:
                nproc = task_procs[comp] = int(comment.split()[3])

            try:
                all_events[wall_time].append(('start', comp, nproc))
            except KeyError:
                all_events[wall_time]= [('start', comp, nproc)]
            if comp not in comp_names:
                comp_names.append(comp)
        elif state == 'finish_task':
            nproc = task_procs[comp]
            try:
                all_events[wall_time].append(('end', comp, nproc))
            except KeyError:
                all_events[wall_time]= [('end', comp, nproc)]
            if comp not in comp_names:
                comp_names.append(comp)

#    for comp in comp_util_map.keys():
#       print "Utilization for Component:", comp
#       print '================================='
#        comp_util = comp_util_map[comp]
#        for wall_time in sorted(comp_util.keys()):
#           print '%-10.4f   %-10d' % (wall_time,  comp_util[wall_time])

    all_times_raw = sorted(all_events.keys())
    cur_util = {}
    plot_data = {}
    for comp in comp_names:
        plot_data[comp] = {}
        cur_util[comp] = 0

    all_plot_times = []
    for wall_time in all_times_raw:
        comp_names_copy = [name for name in comp_names]
        event_list = all_events[wall_time]
        all_plot_times.append(wall_time)
        for (what, comp, nproc) in event_list:
            comp_data = plot_data[comp]
            if (what == 'start'):
                if (wall_time - 0.0001 not in comp_data.keys()):
                    comp_data[wall_time - 0.0003] = cur_util[comp]
                    comp_data[wall_time - 0.0002] = cur_util[comp]
                    comp_data[wall_time - 0.0001] = cur_util[comp]
                    all_plot_times += [wall_time - 0.0003, wall_time - 0.0002, wall_time - 0.0001]
#                    comp_data[wall_time - 0.0001] = cur_util[comp]
                cur_util[comp] += nproc
                comp_data[wall_time] = cur_util[comp]
                try:
                    comp_names_copy.pop(comp_names_copy.index(comp))
                except:
                    pass
            elif (what == 'end'):
                if (wall_time - 0.0001 not in comp_data.keys()):
                    comp_data[wall_time - 0.0003] = cur_util[comp]
                    comp_data[wall_time - 0.0002] = 0
                    comp_data[wall_time - 0.0001] = 0
                    all_plot_times += [wall_time - 0.0003, wall_time - 0.0002, wall_time - 0.0001]
                cur_util[comp] -= nproc
                comp_data[wall_time] = cur_util[comp]
                try:
                    comp_names_copy.pop(comp_names_copy.index(comp))
                except:
                    pass

        for comp in comp_names_copy:
            comp_data = plot_data[comp]
            if (wall_time - 0.0001 not in comp_data.keys()):
                comp_data[wall_time - 0.0003] = cur_util[comp]
                comp_data[wall_time - 0.0002] = cur_util[comp]
                comp_data[wall_time - 0.0001] = cur_util[comp]
            comp_data[wall_time] = cur_util[comp]

    all_times = sorted(all_plot_times)
    comp_names_sorted = sorted(plot_data.keys())
    active_sims = {}
    print '%-15s' % ('Wall Time'),
    for comp in comp_names_sorted:
        print '%-10s' % (comp),
    print'%-10s' % ('Num_sims')

    for wall_time in all_times:
        print '%-15.4f' % wall_time,
        num_sims = 0
        for comp in comp_names_sorted:
            comp_data = plot_data[comp]
            print '%-10d' % (comp_data[wall_time]),
            num_sims += comp_data[wall_time] /task_procs[comp]
        print '%-10d' %  num_sims
        active_sims[wall_time] = num_sims

    x = np.array(all_times)
    y_sum = np.array([0.0 for wall_time in all_times])
    y = {}
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    x0 = np.array([0.0, all_times[-1]])
    y0 = np.array([total_procs, total_procs])
    ax1.plot(x0, y0, linestyle = '--', linewidth = 2)
    colors = ["#CC6666", "#1DACD6", "#6E5160"]
    comp_color = {}
    for comp in comp_names_sorted:
        y[comp] = np.array([plot_data[comp][wall_time] for wall_time in all_times])
        comp_color[comp] = colors.pop(0)
        max_num_comp_sims = max(y[comp]) / task_procs[comp]
#        comp_color[comp] = colors.pop(0)
        y_inc = [0] * len(y[comp])
        y_plot_old = y_sum.copy()
        for i in range(1, max_num_comp_sims + 1):
            for t in range(len(y_inc)):
                y_inc[t] = min(y_inc[t] + task_procs[comp], y[comp][t])
            y_inc_array = np.array(y_inc)
            y_plot = y_inc + y_sum
            if(i == 1):
                ax1.plot(x, y_plot, label = comp, markeredgecolor='c',
                         markerfacecolor=comp_color[comp], color = 'k', linewidth=0.5)
            else:
                ax1.plot(x, y_plot, markeredgecolor='c',
                         markerfacecolor=comp_color[comp], color = 'k', linewidth=0.5)
            plt.fill_between(x, y_plot, y_plot_old, color = comp_color[comp], alpha = 0.5)
            y_plot_old = y_plot
        y_sum = y_plot
    lgd = ax1.legend(numpoints = 2, handletextpad = -0.3)
    lines = lgd.get_lines()
    lgd_texts = lgd.get_texts()
    for i in range(len(lines)):
        l = lines[i]
        comp_name = lgd_texts[i]
        fill_color = comp_color[comp_name.get_text()]
        l.set_linestyle('')
        l.set_marker('s')
        l.set_markersize(12)
        l.set_markevery(2)
        l.set_markerfacecolor(fill_color)
        l.set_alpha(0.5)
        l.set_markeredgecolor('k')
        l.set_markeredgewidth(1.5)
    plt.axis(xmin=0.0)
    plt.xlabel('Wall Time (Sec.)')
    plt.ylabel('Cores Used')
    plt.title('Utilization by component')

    ax2 = fig.add_subplot(212, sharex=ax1)
    x_sims = np.array(all_times_raw)
    y_sims = np.array([active_sims[wall_time] for wall_time in all_times_raw])
#    for times in all_times_raw:
#        print times, active_sims[times]
    ax2.plot(x_sims, y_sims, drawstyle='steps-post')
    plt.axis(xmin=0.0, ymax = max(active_sims.values()) + 1)
    plt.xlabel('Wall Time (Sec.)')
    plt.ylabel('Number of Simulations')
    plt.title('Active concurrent Simulations')
    if len(sys.argv) > 2 and sys.argv[2] == '--save':
        fmt = sys.argv[3]
        plt.savefig(fname+'.' + fmt, format = fmt)
    else:
        plt.show()

    sys.exit(0)
