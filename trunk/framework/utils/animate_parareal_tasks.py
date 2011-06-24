# -*- coding: utf-8 -*-
#! /usr/bin/python

import sys
import subprocess                 
import os
import BeautifulSoup
import urllib2
import numpy as np
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.contour import ContourSet
from matplotlib.ticker import FixedLocator

FPS = 8
SIMSEC_PER_FRAME = 80
PLOT_ALL_CHANGES = False


def format(x, pos=None):
    if x % 2 == 0:
        return '%d' % (x/2)
    else:
        return ''

def plot_task_data(end_time_map, max_slice, max_iteration, max_wall_time):
    
#    print end_time_map, max_slice, max_iteration, max_wall_time
    f = plt.figure(4)
    plt.ylabel('Slice')
    plt.xlabel('Iteration')
    plt.title('%.3f Sec.' % (max_wall_time))
    #print max_iteration, max_slice
    
    num_components = len(end_time_map)
    iterations = np.linspace(1, max_iteration*num_components, max_iteration*num_components)
    slices = np.linspace(1, max_slice, max_slice)
      
    plt.xlim(0, max_iteration*num_components)
    plt.ylim(0, max_slice)
    
    
    #print iterations, slices
#    print [len(iterations), len(slices), len(iterations), len(slices)]
    convergence = np.ma.array(np.zeros([len(iterations), len(slices)]),
                        mask = np.ones((len(iterations), len(slices))))
    X = np.ma.array(np.zeros([len(iterations) + 1, len(slices) + 1]))
    Y = np.ma.array(np.zeros([len(iterations) + 1, len(slices) + 1]))
    
    comp_names = end_time_map.keys()
    for i in range(len(comp_names)):
        offset = (1.0 / num_components) * i
        end_map = end_time_map[comp_names[i]]
        #print end_map
        for ((iteration, slice), value) in sorted(end_map.iteritems()):
    #        print iteration, slice, '%.3e' % (value)
            iter_idx = num_components * iteration + i
            convergence[iter_idx, slice] = value
            convergence.mask[iter_idx, slice] = False
            X[iter_idx, slice] = X[iter_idx, slice + 1] = iter_idx - 1.0
            Y[iter_idx, slice] = Y[iter_idx + 1 , slice] = slice - 0.5
            Y[iter_idx, slice + 1] = Y[iter_idx + 1, slice + 1] = slice + 0.5
            X[iter_idx + 1, slice] = X[iter_idx + 1, slice + 1] = iter_idx
    
        # find minimum value not equal to zero
        value_min = 1000.0
        for ((iteration, slice), value) in sorted(end_map.iteritems()):
            if value > 0.0 and value < value_min:
                value_min = value
                
        # set zeros to value min
        for ((iteration, slice), value) in sorted(end_map.iteritems()):
            if value < value_min:
                #print 'changed ', value
                convergence[iter_idx, slice] = value_min
                #print ' to ', value_min
    fig = plt.figure()
    ax = fig.add_subplot(111)
    try:
#        p = plt.pcolor(X.transpose(), Y.transpose(), convergence.transpose(), norm = LogNorm())
         p = ax.pcolor(X.transpose(), Y.transpose(), convergence.transpose())
    except ValueError:
         p = ax.plot((0), (0))
    else:
        ax.set_xlim([0, 2 * max_iteration + 1])
        ax.set_ylim([0, max_slice + 1])
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Slice')
        ax.xaxis.set_major_formatter(plt.FuncFormatter(format))
        xmajorLocator = FixedLocator(range(2 * max_iteration + 1), 5)
        ax.xaxis.set_major_locator( xmajorLocator )

    filename = 'plot_%09.3f.png' % (max_wall_time)
    plt.savefig(filename, dpi=100)
    print 'Wrote file', filename
    plt.clf()
    return convergence


def get_task_times(url):
    task_map = {}
    all_comp_names = []
    try:
        page = urllib2.urlopen(url)
    except:
        print 'Error retrieving URL ', url
        raise
    parsed_page = BeautifulSoup.BeautifulSoup(page)
    events_table = parsed_page('table')[3]
    events = events_table('tr')[1:]
    events.reverse()
    max_slice = 0
    max_iteration = 0
    for event in events:
        fields = event('td')
        field_values = [field.contents[0].strip() for field in fields]
        phys_stamp = field_values[-2]
        if (field_values[2] == u'IPS_TASK_END'):
            #print ' '.join(field_values)
            comment = field_values[-1]
            comp = field_values[3]
            if comp not in all_comp_names:
                all_comp_names.append(comp)
            comment_fields = comment.split()
            task_id = comment_fields[comment_fields.index('task_id') + 2]
            wall_time = field_values[-3]
            try:
                new_task = task_map[task_id]
            except KeyError:
                new_task = Task(task_id = task_id,
                                end_time = float(wall_time), 
                                phys_time = float(phys_stamp), 
                                comp_name = comp)
                task_map[task_id] = new_task
            else:
                new_task.end_time = float(wall_time)
        elif (field_values[2] in [u'IPS_LAUNCH_TASK_POOL', u'IPS_LAUNCH_TASK']):
            comment = field_values[-1]
            comp = field_values[3]
            wall_time = field_values[-3]
            comment_fields = comment.split()
            task_id = comment_fields[comment_fields.index('task_id')+ 2]
            try:
                tag = comment_fields[comment_fields.index('Tag')+ 2]
            except ValueError :
                if field_values[2] == u'IPS_LAUNCH_TASK':
                    try:
                        (iter, slice) = [int(v) for v in comment.split()[-1].split('.')]
                    except ValueError:
                        (iter, slice) = [int(v) for v in comment.split()[-2].split('.')]
                else:
                    try:
                        (iter, slice) = [int(v) for v in comment.split()[-5].split('.')]
                    except ValueError:
                        (iter, slice) = [int(v) for v in comment.split()[-6].split('.')]
            else:
                (iter, slice) = [int(v) for v in tag.split('.')]

            if iter > max_iteration:
                max_iteration = iter
            if slice > max_slice:
                max_slice = slice
                
            if 'mpiexec' in comment_fields:
                dash_n_idx = comment_fields.index('-n')
                nproc = int(comment_fields[dash_n_idx + 1 ])
            else:
                try:
                    aprun = comment_fields.index('aprun')
                    nproc = int(comment_fields[aprun + 2 ])
                except:
                    raise
            try:
                new_task = task_map[task_id]
            except KeyError:
                new_task = Task(task_id = task_id, 
                                nproc = nproc, 
                                start_time = float(wall_time), 
                                phys_time = float(phys_stamp),
                                comp_name = comp,
                                iteration = iter,
                                slice = slice)
                task_map[task_id] = new_task
            else:
                new_task.nproc = nproc
                new_task.start_time = wall_time
                new_task.phys_time = iter
            if comp not in all_comp_names:
                all_comp_names.append(comp)
                                    
    task_life_map = {}
    for comp in all_comp_names:
        task_life_map[comp] = {}
           
    max_slice += 1
    max_iteration += 1
                    
    max_wall_time = -1.0
    last_event = events[-1]
    fields = last_event('td')
    field_values = [field.contents[0].strip() for field in fields]
    last_frame_time = -1.0
    
    first_plot = True
    for event in events:
        fields = event('td')
        field_values = [field.contents[0].strip() for field in fields]
        comment = field_values[-1]
        comp = field_values[3]
        comment_fields = comment.split()
        wall_time = float(field_values[-3])
        update_plot = False
        value = None
        if (field_values[2] == u'IPS_TASK_END'):
            #print ' '.join(field_values)
            task_id = comment_fields[comment_fields.index('task_id') + 2]
            task = task_map[task_id]
            slice = task.slice
            iteration = task.iteration
            task_life = task_life_map[comp]
            value = float(task_life_map.keys().index(comp)) + 1.0
            update_plot = True
            #print '###', iteration, slice, task_id, task_life[iteration, slice]
        elif (field_values[2] in [u'IPS_LAUNCH_TASK_POOL', u'IPS_LAUNCH_TASK']):
            task_id = comment_fields[comment_fields.index('task_id')+ 2]
            task = task_map[task_id]
            slice = task.slice
            iteration = task.iteration
            task_life = task_life_map[comp]
            value = float(task_life_map.keys().index(comp)) + 0.5
            update_plot = True
            
        if wall_time > max_wall_time:
            max_wall_time = wall_time
            
        if wall_time - last_frame_time > SIMSEC_PER_FRAME :
            for ptime in np.arange(last_frame_time + SIMSEC_PER_FRAME, wall_time, SIMSEC_PER_FRAME):
                plot_task_data(task_life_map, max_slice, max_iteration, ptime)
                last_frame_time = ptime
                    
        if update_plot:
            task_life[iteration, slice] = value
            if (PLOT_ALL_CHANGES or first_plot):
                print max_slice, max_iteration, wall_time
                plot_task_data(task_life_map, max_slice, max_iteration, wall_time)
                last_frame_time = wall_time
                first_plot = False
            
    #Plot Final state
    plot_task_data(task_life_map, max_slice, max_iteration, wall_time)

#        if (update_plot):
#            task_life[iteration, slice] = value
#           plot_task_data(task_life_map, max_slice, max_iteration, wall_time)
#           last_frame_time = wall_time
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
        
#os.spawnvp(os.P_WAIT, 'mencoder', command)

    print "\n\nabout to execute:\n%s\n\n" % ' '.join(command)
    subprocess.check_call(command)

    print "\n\n The movie was written to 'output.avi'"

    print "\n\n You may want to delete *.png now.\n\n"


class Task(object):
    def __init__(self, 
                 task_id = None, 
                 nproc = -1, 
                 start_time = -1.0, 
                 end_time = -1.0, 
                 phys_time = -1.0, 
                 comp_name = '', 
                 iteration = 0,
                 slice = 0):
        self.task_id = task_id
        self.nproc = nproc
        self.start_time = start_time
        self.end_time = end_time
        self.phys_time = phys_time
        self.comp_name = comp_name
        self.iteration = iteration
        self.slice = slice
        
    pass
                

if __name__ == '__main__':
    get_task_times(sys.argv[1])
    sys.exit(0)
