#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

import sys
from . import BeautifulSoup
import urllib.request
import urllib.error
import urllib.parse
PLOT = True
try:
    from pylab import figure, xlabel, ylabel, title, grid, plot, show, legend
except:
    PLOT = False


def plot_exec_time(task_time_map):
    figure()
    for (comp_name, time_map) in list(task_time_map.items()):
        x = [float(k) for k in sorted(list(time_map.keys()), key=float)]
        y = [float(time_map[k]) for k in sorted(list(time_map.keys()), key=float)]
        plot(x, y, label=comp_name)
    legend()
    xlabel('Physics Time')
    ylabel('Task execution Time')
    title('Execution time for IPS tasks')
    grid(True)
    show()


def get_task_times(url_list):
    phys_time_map = {}
    for url in url_list:
        try:
            page = urllib.request.urlopen(url)
        except:
            print('Error retreiving URL ', url)
            raise
        parsed_page = BeautifulSoup.BeautifulSoup(page)
        events_table = parsed_page('table')[3]
        events = events_table('tr')[1:]
        sim_time_map = {}
        phys_exec_time = {}
        for event in events:
            fields = event('td')
            field_values = [field.contents[0].strip() for field in fields]
            phys_time = field_values[6]
            wall_time = float(field_values[5])
            # print field_values[2]
            if (field_values[2] == 'IPS_UPDATE_TIME_STAMP'):
                sim_time_map[phys_time] = float(wall_time)
        sorted_keys = sorted(list(sim_time_map.keys()), key=float)
        for k in range(1, len(sorted_keys)):
            cur_step = sorted_keys[k]
            prior_step = sorted_keys[k - 1]
            numer = sim_time_map[cur_step] - sim_time_map[prior_step]
            denum = float(cur_step) - float(prior_step)
            phys_exec_time[cur_step] = numer / denum
            try:
                phys_time_map[cur_step].append(phys_exec_time[cur_step])
            except KeyError:
                phys_time_map[cur_step] = [phys_exec_time[cur_step]]
            # print cur_step, phys_exec_time[cur_step], phys_time_map[cur_step]

    print('Physics Time         Time/Physics Sec.')
    x = []
    y = []
    for k in sorted(list(phys_time_map.keys()), key=float):
        val = sum(phys_time_map[k]) / len(phys_time_map[k])
        print(k, val)
        x.append(float(k))
        y.append(val)

    if (PLOT):
        figure()
#        x = [float(k) for k in sorted(plot_data.keys(), key = float)]
#        y = [plot_data[p] for p in sorted(plot_data.keys())]
        plot(x, y)
        xlabel('Physics Time')
        ylabel('Wall Time')
        title('Simulation wall clock consumption rate')
        grid(True)
        show()


if __name__ == '__main__':
    get_task_times(sys.argv[1:])
    sys.exit(0)
