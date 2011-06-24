
""" Wrapper for publishing FSP_data Events """

import os
import socket
import time
from Events import publish_event

def FSP_data_addMD(aid, name, type='', loc='', ts='', sl=0, size=-1):
    topic = 'FSP_data'
    aidstr = 'aid=\"' + aid + '\" '
    namestr = 'name=\"' + name + '\" '
    typestr = 'type=\"' + type + '\" '
    slstr = 'sl=\"' + str(sl) + '\" '
    if (loc == ''):
	hostname = socket.gethostname()
	pwd = os.getcwd()
	loc = hostname + ':' + pwd + '/' + name
    locstr = 'loc=\"' + loc + '\" '	
    if (ts == ''):
	ts = time.ctime(os.path.getmtime(pwd+'/'+name)-time.timezone)
    tsstr = 'ts=\"' + ts + '\" '	
    if (size == -1):
	size = os.path.getsize(pwd+'/'+name)
    sizestr = 'size=\"' + str(size) + '\" '
    message = "<addMD "+''.join([aidstr, namestr, typestr, locstr, tsstr, slstr, sizestr])+"/>"
    publish_event(message, topic)	
    return
