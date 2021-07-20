#!/usr/bin/env python
# -------------------------------------------------------------------------------
#  Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

import sys
from urllib import request, error
import socket
import time
import traceback

headers = {'Content-Type': 'application/json'}


def sendEncodedMessage(url, msg):
    if not isinstance(msg, bytes):
        msg = msg.encode('utf-8')

    num_trials = 2
    trial = 0
    delay = [0.4, 0.8, 1.2]

    while trial < num_trials:
        try:
            req = request.Request(url, data=msg, headers=headers, method='POST')
            resp = request.urlopen(req)
        except error.URLError:
            trial += 1
            if trial > num_trials:
                open('PORTAL.err', 'a').write('%s\n' % (msg))
            else:
                time.sleep(delay[trial-1])
        else:
            break
    try:
        resp.close()
    except Exception:
        pass


if __name__ == "__main__":
    """ Loop over input from stdin, expecting lines of the format:
        URL ENCODED_WEB_MSG
    """
    timeout = 3
    socket.setdefaulttimeout(timeout)
    error_f = open("sendpost.err", 'w')
    line = '   '
    while True:
        try:
            line = sys.stdin.readline().rstrip('\n')
            if line == '':
                break
            tokens = line.split(' ', 1)
            sendEncodedMessage(tokens[0], tokens[1])
        except Exception:
            traceback.print_exc(file=error_f)
    sys.exit(0)
