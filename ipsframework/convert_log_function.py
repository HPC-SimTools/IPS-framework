#!/usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
import os
import HTML


def parse_log_line(l):
    tokens = l.split()

    ret_fields = ['event_time', 'event_num', 'eventtype', 'code', 'state', 'walltime',
                  'phystimestamp', 'comment']
    field_names = ['code', 'eventtype', 'ok', 'walltime', 'state', 'comment', 'sim_name',
                   'portal_runid', 'seqnum', 'phystimestamp']

    val_dict = {}

    val_dict['event_num'] = tokens[0]
    val_dict['event_time'] = tokens[1]

    start = {s: l.find(s) + len(s + "=") for s in field_names}
    end = {s: l.find("'", start[s] + 1) if l[start[s]] == "'" else \
        l.find(" ", start[s] + 1) for s in field_names}
    for k in end:
        if end[k] == -1:
            end[k] = len(l)
        if l[start[k]] == "'":
            start[k] += 1
    val_dict.update({s: l[start[s]:end[s]] for s in field_names})
    ret_list = [val_dict[k].strip("'") for k in ret_fields]

    return ret_list


def convert_logdata_to_html(lines):
    if type(lines).__name__ == 'str':
        lines = [l for l in lines.split('\n') if l != '']
    # lines.reverse()
    tokens = []
    for l in lines:
        if 'IPS_RESOURCE_ALLOC' not in l and 'IPS_START' not in l and 'IPS_END' not in l:
            tmp = parse_log_line(l)
            tokens.append(tmp)
    header = ['Time', 'Sequence Num', 'Type', 'Code', 'State', 'Wall Time',
              'Physics Time', 'Comment']

    html_page = HTML.table(tokens, header_row=header)
    return html_page


def convert_log_to_html(fname):
    lines = open(fname).readlines()
    return convert_logdata_to_html(lines)
