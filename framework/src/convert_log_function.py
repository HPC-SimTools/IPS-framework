#!/usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
import os
import HTML


def parse_log_line(l):
    tokens = l.split()
    event_num = tokens[0]
    e_time = tokens[1]

    fields = ['event_num', 'event_time', 'comment', 'code', 'ok', 'portal_runid', 'eventtype', 'phystimestamp',
              'state', 'seqnum', 'walltime']

    ret_fields = ['event_time', 'event_num', 'eventtype', 'code', 'state', 'walltime',
                  'phystimestamp', 'comment']
    start = {}
    end = {}
    val_dict = {}

    val_dict['event_num'] = tokens[0]
    val_dict['event_time'] = tokens[1]

    start[fields[2]] = l.find(fields[2] + '=') + len(fields[2]) + 1
    end[fields[2]] = l.find(fields[3] + '=') - 1
    val_dict[fields[2]] = l[start[fields[2]]: end[fields[2]]]

    for i in range(3, len(fields) - 1):
        start[fields[i]] = end[fields[i - 1]] + len(fields[i]) + 2
        end[fields[i]] = l.find(fields[i + 1] + '=', start[fields[i]]) - 1
        val_dict[fields[i]] = l[start[fields[i]]: end[fields[i]]]

    start['walltime'] = end['seqnum'] + 1 + len('walltime=')
    end['walltime'] = l.find('\r\n', start['walltime'])
    val_dict['walltime'] = l[start['walltime']: end['walltime']]

    ret_list = [val_dict[k].strip("'") for k in ret_fields]

    comment_start = l.find("comment=") + len("comment=")
    comment_end = l.find("code=") - 1
    comment = l[comment_start:comment_end]
    comment = comment.strip("'")

    code_start = comment_end + 1 + len("code=")
    code_end = l.find(" ok=", code_start)
    code = l[code_start:code_end]

    ok_start = code_end + 1 + len('ok=')
    ok_end = l.find('portal_runid=', ok_start) - 1
    ok = l[ok_start:ok_end]

    runid_start = ok_end = 1 + len('portal_runid=')
    runid_end = l.find('eventtype=', runid_start) - 1
    runid = l[runid_start:runid_end]

    type_start = runid_end + 1 + len('eventtype=')
    type_end = l.find('phystimestamp=', type_start) - 1
    event_type = l[type_start:type_end]

    tstamp_start = type_end + 1 + len('phystimestamp=')
    tstamp_end = l.find('state=', tstamp_start) - 1
    tstamp = l[tstamp_start:tstamp_end]

    state_start = tstamp_end + 1 + len('state=')
    state_end = l.find('seqnum=', state_start) - 1
    state = l[state_start:state_end]

    seqnum_start = state_end + 1 + len('seqnum=')
    seqnum_end = l.find('walltime=', seqnum_start) - 1
    seqnum = l[seqnum_start:seqnum_end]

    walltime_start = seqnum_end + 1 + len('walltime=')
    walltime_end = l.find('\r\n', walltime_start)
    walltime = l[walltime_start:walltime_end]

    # print ret_list
    #    print event_num, e_time, code, ok, runid, event_type, tstamp, state, seqnum, walltime
    #    print [e_time, event_num, event_type, code, state, walltime, tstamp, comment]
    #    print val_dict
    return ret_list


def convert_logdata_to_html(lines):
    if type(lines).__name__ == 'str':
        lines = [l for l in lines.split('\n') if l != '']
    # lines.reverse()
    tokens = []
    for l in lines:
        if 'IPS_RESOURCE_ALLOC' not in l and 'IPS_START' not in l and 'IPS_END' not in l:
            tokens.append(parse_log_line(l))
            # print tokens
    header = ['Time', 'Sequence Num', 'Type', 'Code', 'State', 'Wall Time',
              'Physics Time', 'Comment']

    html_page = HTML.table(tokens, header_row=header)
    return html_page


def convert_log_to_html(fname):
    lines = open(fname).readlines()
    return convert_logdata_to_html(lines)
