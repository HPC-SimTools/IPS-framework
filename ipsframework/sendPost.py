#! /usr/bin/env python
# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------

import sys
import urllib.request
import urllib.error
import urllib.parse
import socket
import time
import traceback

# timeout in seconds


def sendEncodedMessage(url, msg):
    global msg_queue
    num_trials = 2
    trial = 0
    delay = [0.4, 0.8, 1.2]

    while (trial < num_trials):
        try:
            f = urllib.request.urlopen(url, msg)
        except (urllib.error.URLError):
            trial += 1
            if trial > num_trials:
                open('PORTAL.err', 'a').write('%s\n' % (msg))
            else:
                time.sleep(delay[trial - 1])
        else:
            break
    try:
        f.close()
    except Exception:
        pass


if __name__ == "__main__":
    """ Loop over input from stdin, expecting lines of the format:
        URL ENCODED_WEB_MSG
    """
    timeout = 3
    socket.setdefaulttimeout(timeout)
    error_f = open("sendpost.err", 'a')
    l = '   '
    while (l != ''):
        try:
            l = sys.stdin.readline().rstrip('\n')
            tokens = l.split(' ', 1)
            url = tokens[0]
            msg = tokens[1]
            sendEncodedMessage(url, msg)
        except Exception:
            traceback.print_exc(file=error_f)
    sys.exit(0)
