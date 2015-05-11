#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import os
from configobj import ConfigObj
import ipsutil


def get_status(checklist_file):
    ips_status={}
    ips_status['CREATE_RUNSPACE'] = False
    ips_status['RUN_SETUP'] = False
    ips_status['RUN'] = False

    try:
        f = open(checklist_file,'r')
        conf = ConfigObj(checklist_file, interpolation = 'template', file_error = True)

        if conf['CREATE_RUNSPACE'] == 'DONE':
            ips_status['CREATE_RUNSPACE'] = True
        elif conf['CREATE_RUNSPACE'] == 'NOT_DONE':
            ips_status['CREATE_RUNSPACE'] = False

        if conf['RUN_SETUP'] == 'DONE':
            ips_status['RUN_SETUP'] = True
        elif conf['RUN_SETUP'] == 'NOT_DONE':
            ips_status['RUN_SETUP'] = False

        if conf['RUN'] == 'DONE':
            ips_status['RUN'] = True
        elif conf['RUN'] == 'NOT_DONE':
            ips_status['RUN'] = False

    except IOError, ioe:
        print 'Checklist config file "%s" could not be found, continuing without.' % checklist_file
    except SyntaxError, (ex):
        print 'Error parsing config file: %s' % checklist_file
        raise
    except Exception, e:
        print 'encountered exception during fwk.run() checklist configuration'
    finally:
        f = open(checklist_file, 'w')
        conf = ConfigObj(checklist_file, interpolation = 'template', file_error = True)
        conf['CREATE_RUNSPACE'] = False
        conf['RUN_SETUP'] = False
        conf['RUN'] = False
        conf.write()

    return ips_status



def update(checklist_file,ips_status):

    try:
        conf = ConfigObj(checklist_file, interpolation = 'template', file_error = True)
    except IOError, ioe:
        #SEK: Remove because for the create_runspace it is not there?
        #print 'Checklist config file "%s" could not be found, continuing without.' % checklist_file
        return '', ips_status
    except SyntaxError, (ex):
        errmsg='Error parsing config file: ' + checklist_file
        return errmsg, ips_status
    except Exception, e:
        print e
        return 'encountered exception during fwk.run() checklist status', ips_status
    # Make it general to be able to take fullpath or relative path
    for step in ['CREATE_RUNSPACE','RUN_SETUP','RUN']:
        if ips_status[step]:
            conf[step] = 'DONE'
        else:
            conf[step] = 'NOT_DONE'
        print step + ' = ' + conf[step]
    conf.write()

    return
