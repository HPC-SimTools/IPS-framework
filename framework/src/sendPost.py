#! /usr/bin/env python

import sys
import urllib2
import socket
import time

# timeout in seconds

def sendEncodedMessage(url, msg):
    global msg_queue
    num_trials = 2
    trial = 0
    delay = [0.4, 0.8, 1.2]
    
    while (trial < num_trials):
        try:
            f = urllib2.urlopen(url, msg)
        except (urllib2.URLError), e :
            trial += 1
            if trial > num_trials:
                open('PORTAL.err', 'a').write('%s\n'% (msg))
            else:
                time.sleep(delay[trial-1])
        else:
            break
    try:
        f.close()
    except:
        pass
        

if __name__ == "__main__":
    """ Loop over input from stdin, expecting lines of the format:
        URL ENCODED_WEB_MSG
    """
    timeout = 3
    socket.setdefaulttimeout(timeout)
    l = sys.stdin.readline().rstrip('\n')
    while (l != ''):
        tokens = l.split(' ', 1)
        url = tokens[0]
        msg = tokens[1]
        sendEncodedMessage(url, msg)
        l = sys.stdin.readline().rstrip('\n')
    sys.exit(0)
