# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
from ipsframework.utils import HTML


def parse_log_line(line):
    tokens = line.split()

    ret_fields = ['event_time', 'event_num', 'eventtype', 'code', 'state', 'walltime',
                  'phystimestamp', 'comment']
    field_names = ['code', 'eventtype', 'ok', 'walltime', 'state', 'comment', 'sim_name',
                   'portal_runid', 'seqnum', 'phystimestamp']

    val_dict = {}

    val_dict['event_num'] = tokens[0]
    val_dict['event_time'] = tokens[1]

    start = {s: line.find(s) + len(s + "=") for s in field_names}
    end = {s: line.find("'", start[s] + 1) if line[start[s]] == "'" else line.find(" ", start[s] + 1) for s in field_names}
    for k in end:
        if end[k] == -1:
            end[k] = len(line)
        if line[start[k]] == "'":
            start[k] += 1
    val_dict.update({s: line[start[s]:end[s]] for s in field_names})
    ret_list = [val_dict[k].strip("'") for k in ret_fields]

    return ret_list


def convert_logdata_to_html(lines):
    if type(lines).__name__ == 'str':
        lines = [line for line in lines.split('\n') if line != '']
    tokens = []
    for line in lines:
        if 'IPS_RESOURCE_ALLOC' not in line and 'IPS_START' not in line and 'IPS_END' not in line:
            tmp = parse_log_line(line)
            tokens.append(tmp)
    header = ['Time', 'Sequence Num', 'Type', 'Code', 'State', 'Wall Time',
              'Physics Time', 'Comment']

    html_page = HTML.table(tokens, header_row=header)
    return html_page
