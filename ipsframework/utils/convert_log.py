#!/usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import sys
import os


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


fname = sys.argv[1]
lines = open(fname).readlines()
lines.reverse()
tokens = []
for l in lines[1:-2]:
    if 'IPS_RESOURCE_ALLOC' not in l:
        tokens.append(parse_log_line(l))
        # print tokens
page = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd" >
<head>
<title>SWIM Monitor</title>
</head>
<body>
<body>

<table>
<tr><td><a href="/vote?id=18836"><img src="/media/images/starplus.png" /></a></td>
<td rowspan=2><img src="/media/images/star1.png" /></td>
<td rowspan=2><a href="/purge?id=18836"><img src="/media/images/icon_purge.png" alt="Purge" width="20"/></a></td></tr>
<tr><td><a href="/veto?id=18836"><img src="/media/images/starminus.png" /></a></td></tr>
</table>
<p></p>

<table>
<tr><td><a href="/vote?id=18836"><img src="/media/images/starplus.png" /></a></td>
<td rowspan=2><img src="/media/images/star1.png" /></td>
<td rowspan=2><a href="/purge?id=18836"><img src="/media/images/icon_purge.png" alt="Purge" width="20"/></a></td></tr>
<tr><td><a href="/veto?id=18836"><img src="/media/images/starminus.png" /></a></td></tr>
</table>
<p></p>

<table width=100% class="greyTB"  style='table-layout:fixed' style="width:99%;" align="center" cellpadding="0" cellspacing="0">
 <col width=30% >
 <col width=70% >
<tr><td class="blueCell">Run Comment:</td><td> Some Comment </td><tr>
<tr><td class="blueCell">Tokamak:</td><td>TOKAMAK</td><tr>
<tr><td class="blueCell">Shot No:</td><td>NUM</td><tr>
<tr><td class="blueCell">Sim Name:</td><td>SIM</td><tr>
<tr><td class="blueCell">Sim Runid:</td><td>RUNID</td><tr>
<tr><td class="blueCell">Last Updated</td><td>TIME</td><tr>
<tr><td class="blueCell">Host:</td><td>MACHINE</td><tr>
<tr><td class="blueCell">Output Prefix: </td><td>N/A</td><tr>
<tr><td class="blueCell">Tag: </td><td>N/A</td><tr>
<tr><td class="blueCell">Logfile: </td><td>N/A</td><tr>
<tr><td class="blueCell">Visualization URL: </td><td>N/A</td>
</table>

<p></p>
<table style="width:100%;" align="center" cellpadding="0" cellspacing="0">
 <col width=40>
 <col width=40>
 <col width=139>
 <col width=190>
 <col width=70>
 <col width=50>
 <col width=50>
 <col width=445>

<tr><td>Time</td><td>Seq Num</td><td>Event Type</td><td>Code</td><td>State</td><td>Wall Time</td><td>Phys Time-<br>stamp</td><td>Comment</tr>

@TABLE_BODY@

</table>
        </div><!-- end outer -->
        <div id="footer"><h1>SWIM Team (2010) </h1></div>
</div><!-- end container -->
</body>
</html>
"""

table_body = ''
for token_line in tokens:
    table_body += '<tr>'
    # print token_line
    for token in token_line:
        table_body += '<td> %s </td>' % (token)
    table_body += '</tr> \n\n'

html_page = str(page).replace('@TABLE_BODY@', table_body)
print(html_page)
