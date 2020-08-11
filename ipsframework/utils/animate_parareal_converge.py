#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
# -*- coding: utf-8 -*-

import sys
import subprocess
import BeautifulSoup
import urllib.request
import urllib.error
import urllib.parse
import numpy as np

NUM_FRAMES = 100
FPS = 4
SIMSEC_PER_FRAME = 20

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
except:
    raise


def animate_convergence(converge, max_slice, max_iteration, max_wall_time):

    f = plt.figure(4)
    plt.ylabel('Slice')
    plt.xlabel('Iteration')
    plt.title('%.3f Sec.' % (max_wall_time))
    plt.xlim(0, max_iteration)
    plt.ylim(0, max_slice)
    # print max_iteration, max_slice
    iterations = np.linspace(1, max_iteration, max_iteration)
    slices = np.linspace(1, max_slice, max_slice)
    # print iterations, slices
#    print [len(iterations), len(slices), len(iterations), len(slices)]
    convergence = np.ma.array(np.zeros([len(iterations), len(slices)]),
                              mask=np.ones((len(iterations), len(slices))))
    X = np.ma.array(np.zeros([len(iterations) + 1, len(slices) + 1]))
    Y = np.ma.array(np.zeros([len(iterations) + 1, len(slices) + 1]))
    X1 = np.zeros(len(iterations) + 1)
    Y1 = np.zeros(len(slices) + 1)
    Z1 = np.ones([len(slices) + 1, len(iterations) + 1])
    for i in range(len(X1)):
        X1[i] = i
    for i in range(len(Y1)):
        Y1[i] = i

    for ((iteration, slice), value) in sorted(converge.items()):
        convergence[iteration, slice] = value
        convergence.mask[iteration, slice] = False
        X[iteration, slice] = X[iteration, slice + 1] = iteration - 0.5
        Y[iteration, slice] = Y[iteration + 1, slice] = slice - 0.5
        Y[iteration, slice + 1] = Y[iteration + 1, slice + 1] = slice + 0.5
        X[iteration + 1, slice] = X[iteration + 1, slice + 1] = iteration + 0.5

    # print iterations
    # print slices
    # find minimum value not equal to zero
    value_min = 1000.0
    for ((iteration, slice), value) in sorted(converge.items()):
        if value > 0.0 and value < value_min:
            value_min = value
            # print 'min = ', value_min

    # set zeros to value min
    for ((iteration, slice), value) in sorted(converge.items()):
        if value < value_min:
            # print 'changed ', value
            convergence[iteration, slice] = value_min
            # print ' to ', value_min
    try:
        p = plt.pcolor(X.transpose(), Y.transpose(), convergence.transpose(),
                       norm=LogNorm())
    except ValueError:
        p = plt.plot((0), (0))
    else:
        tol_level = [1.5e-6]
        # CS = plt.contour(X1, Y1, Z1, levels = tol_level)

        cb = plt.colorbar(spacing='proportional', format='%.1e')
        # cb.add_line(CS)
        cb.ax.set_ylabel('Error')

    filename = 'plot_%09.3f.png' % (max_wall_time)
    plt.savefig(filename, dpi=100)
    print('Wrote file', filename)
    plt.clf()


def get_task_times(url_list):
    task_time_map = {}
    all_phys_stamps = set()
    converge = {}
    anim_converge = {}
    for url in url_list:
        try:
            page = urllib.request.urlopen(url)
        except:
            print('Error retreiving URL ', url)
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
            event_num = field_values[1]
            wall_time = float(field_values[-3])
            if (field_values[2] == 'IPS_LAUNCH_TASK' or field_values[2] == 'IPS_LAUNCH_TASK_POOL'):
                comment_lst = comment.split()
                task_id = comment_lst[comment_lst.index('task_id') + 2]
                try:
                    tag = comment_lst[comment_lst.index('Tag') + 2]
                except ValueError:
                    if field_values[2] == 'IPS_LAUNCH_TASK':
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

                # (phys_stamp, slice) = identifier.split('.')
                # print phys_stamp, identifier, comment.split()[-2]
                if float(phys_stamp_portal) > 0.0:
                    phys_stamp = phys_stamp_portal
                phys_stamp_map[task_id] = (phys_stamp, slice)
            elif (field_values[2] == 'IPS_TASK_END'):
                task_id = comment.split()[2]
                (phys_stamp, slice) = phys_stamp_map[task_id]
                # print ' '.join(field_values)
                exec_time = comment.split()[-2]
                print('%s.%s  %10s  %s' % (phys_stamp, slice, task_id, exec_time))
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
            elif (field_values[2] == 'converge_out'):
                (iteration, slice, value) = comment.split()
                array_idx = int(iteration), int(slice)
                converge[array_idx] = float(value)
                anim_converge[int(event_num)] = (array_idx, wall_time)

    print('Phys_stamp', end=' ')
    for comp in list(task_time_map.keys()):
        for suffix in ['_count', '_low', '_high', '_mean']:
            print(',   ', comp + suffix, end=' ')
    print()

    for phys_stamp in sorted(all_phys_stamps, key=float):
        print(phys_stamp, end=' ')
        for comp_map in list(task_time_map.values()):
            # print comp_map
            try:
                (low, high, mean, values) = comp_map[phys_stamp]
                print(',   ', len(values), ',', low, ',', high, ',', mean, end=' ')
            except KeyError:
                print(',   ,    ,    ,     ,    ,')
        print()

    if (len(converge) > 0):
        max_slice = -1
        max_iteration = -1
        for (iteration, slice) in list(converge.keys()):
            if iteration > max_iteration:
                max_iteration = iteration
            if (slice > max_slice):
                max_slice = slice
        max_slice += 1
        max_iteration += 1

    converge_event_sorted = sorted(anim_converge.keys())
    interval = len(events) / NUM_FRAMES
    last_event_lst = list(range(0, len(events), interval))
    if last_event_lst[-1] != len(events):
        last_event_lst[-1] = len(events)
    event_idx = converge_event_sorted[0]
    plot_idx = 1

    partial_converge = {}
    max_wall_time = -1.0
    last_event = events[-1]
    fields = last_event('td')
    field_values = [field.contents[0].strip() for field in fields]
    total_wall_time = float(field_values[-3])
    time_lst = list(range(0, int(total_wall_time + 1), SIMSEC_PER_FRAME))
    last_frame_time = -1.0
    for event in events:
        fields = event('td')
        field_values = [field.contents[0].strip() for field in fields]
        event_num = int(field_values[1])
        wall_time = float(field_values[-3])
        try:
            (array_idx, wall_time) = anim_converge[event_num]
        except KeyError:
            pass
        else:
            partial_converge[array_idx] = converge[array_idx]

        if wall_time > max_wall_time:
            max_wall_time = wall_time

        if wall_time >= time_lst[plot_idx]:
            if (wall_time - last_frame_time >= SIMSEC_PER_FRAME):
                animate_convergence(partial_converge, max_slice, max_iteration, max_wall_time)
                plot_idx += 1
                last_frame_time = wall_time
            if plot_idx >= len(time_lst):
                break

#
# Now that we have graphed images of the dataset, we will stitch them
# together using Mencoder to create a movie.  Each image will become
# a single frame in the movie.
#
# We want to use Python to make what would normally be a command line
# call to Mencoder.  Specifically, the command line call we want to
# emulate is (without the initial '#'):
# mencoder mf://*.png -mf type=png:w=800:h=600:fps=25 -ovc lavc -lavcopts vcodec=mpeg4 -oac copy -o output.avi
# See the MPlayer and Mencoder documentation for details.
#

    command = ('mencoder',
               'mf://*.png',
               '-mf',
               'type=png:w=800:h=600:fps=%d' % (FPS),
               '-ovc',
               'lavc',
               '-lavcopts',
               'vcodec=mpeg4',
               '-oac',
               'copy',
               '-o',
               'output.avi')

# os.spawnvp(os.P_WAIT, 'mencoder', command)

    print("\n\nabout to execute:\n%s\n\n" % ' '.join(command))
    subprocess.check_call(command)

    print("\n\n The movie was written to 'output.avi'")

    print("\n\n You may want to delete *.png now.\n\n")


if __name__ == '__main__':
    get_task_times(sys.argv[1:])
    sys.exit(0)
