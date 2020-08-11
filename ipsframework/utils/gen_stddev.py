#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
This script will scrape the SWIM portal to extract the task timings of a run and give you the
mean and standard deviation of each task invocation in the given range.  You should use
exec_timer.py to inspect the runtime data visually to come up with the slices.  Slices are
based on physics time steps, and are numbered from 0 to last time step - 1.  You will need to
know what the granularity of the timesteps are and how they map to the graph from exec_timer.py.

This data can then be used to construct accurate models of the run using different phases in RUS.

To run:
python gen_stddev.py -r <portal runid> -b <beginning of slice> -e <end of slice>
"""
import sys
import BeautifulSoup
import urllib.request
import urllib.error
import urllib.parse
import getopt
PLOT = True
try:
    from numpy import array
except:
    PLOT = False

beg = 0
end = -1


def get_task_times():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'r:b:e:', ['run=', 'begin=', 'end='])
    except getopt.GetoptError as err:
        print('problems with command line args')
        sys.exit(2)

    try:
        for o, a in opts:
            if o == '-r' or o == '--run':
                url = "http://swim.gat.com:8080/detail/?id=" + a
            elif o == '-b' or o == '--begin':
                beg = int(a)
            elif o == '-e' or o == '--end':
                end = int(a)
            else:
                print("you did not follow directions")
                sys.exit(2)
    except:
        print("problems....")
        sys.exit(2)

    task_time_map = {}
    all_phys_stamps = set()
    try:
        page = urllib.request.urlopen(url)
    except:
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
            comp_task = field_values[3]
            comment = field_values[-1]
            exec_time = comment.split()[-2]
            phys_stamp = field_values[-2]
            # print phys_stamp, comp_task, exec_time
            try:
                comp_task_map = task_time_map[comp_task]
            except KeyError:
                comp_task_map = {}
                task_time_map[comp_task] = comp_task_map
            comp_task_map[phys_stamp] = exec_time
            all_phys_stamps.add(phys_stamp)

    print('Phys_stamp', end=' ')
    for comp in list(task_time_map.keys()):
        print(',   ', comp, end=' ')
    print()

    for phys_stamp in sorted(all_phys_stamps, key=float):
        print(phys_stamp, end=' ')
        for comp_map in list(task_time_map.values()):
            # print comp_map
            try:
                print(',   ', comp_map[phys_stamp], end=' ')
            except KeyError:
                print(',           ', end=' ')
                comp_map[phys_stamp] = 'Nan'
        print()
    n_arrays = {}
    for (comp_name, time_map) in list(task_time_map.items()):
        x = [float(k) for k in sorted(list(time_map.keys()), key=float)]
        y = [float(time_map[k]) for k in sorted(list(time_map.keys()), key=float)]
        n_arrays.update({comp_name: array([float(time_map[k]) for k in sorted(list(time_map.keys()), key=float)])})
    for c, a in list(n_arrays.items()):
        print(a[0], beg + end, len(a))
        print("Comp:", c, "Mean:", a[beg:end].mean(), "Standard Dev:", a[beg:end].std())


if __name__ == '__main__':
    get_task_times()
    sys.exit(0)
