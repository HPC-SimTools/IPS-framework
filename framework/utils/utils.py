"""
Set of assorted utilities for the FSP project python framework.  Includes

AddSysPath(new_path): add to the path in os-independent way

create_dir(start = os.curdir): setup a new subdirectory in the start one,
    with naming convention userid/datestamp. Use for independent runs of
    the same component.

Publish_outputList(): publish the list of output files (and locations)
    resulting from a component's run

Check_InputFiles(): make sure the invoice sheet of input files needed is
    available for the execution.

Populate_newdir(newdir): Fill in a newly created subdirectory with copies of
    or links to needed files for a run

Randall Bramley
Department of Computer Science
Indiana University
Bloomington, IN 47405
bramley@cs.indiana.edu

"""
from time import time, ctime, sleep
from Events import *
def AddSysPath(new_path):
    """Platform-independent way of adding to the search path for python"""
    import sys, os

    # standardise
    new_path = os.path.abspath(new_path)

    # MS-Windows does not respect case
    if sys.platform == 'win32':
        new_path = new_path.lower()

    # disallow bad paths
    do = -1
    if os.path.exists(new_path):
        do = 1
        
        # check against all paths currently available
        for x in sys.path:
            x = os.path.abspath(x)
            if sys.platform == 'win32':
                x = x.lower()
            if new_path in (x, x + os.sep):
                do = 0

        # add path if we don't already have it
        if do:
            # sys.path.append(new_path)      # Appends to path
            sys.path.insert(0, new_path)   # Prepends to path
            pass

    return do

#=========================================================================

"""----------------------------------------------------------------------
createdir.py:
Try to create a new subdirectory in the current one, which has the
user name and timestamp as the directory name. This would then be
used for each new invocation of the component calling it. 
---------------------------------------------------------------------"""
import os, sys, sre
#-------------------------------------------------------------------
# Number of seconds to wait between attempts to create a new 
# timestamped directory.  Maybe replace with a simple subnumbering
# system would be better, especially for systems with broken clocks.
#-------------------------------------------------------------------
delay = 1

#------------------------------------------------------------
# How many times to try before following W.C. Field's advice:
#------------------------------------------------------------
number_of_tries = 4

def create_dir(start = os.curdir):
#---------------------------------------------------------------------------
#                      ^^^^^^^^^
#                      |||||||||
#
# In Unix, this is just '.' - the os module makes this work for Win,Unix,Mac
#---------------------------------------------------------------------------

    timestamp = ctime(time())
    #---------------------------------------------------------
    # Replace blanks in timestamp with underscores
    # Not required, I just don't like spaces in dir/file names
    #---------------------------------------------------------
    timestamp = timestamp.replace(' ', '_')
    user = os.environ['USER']

    dir_listing = os.listdir(start)
    # trial_dir = os.path.abspath(start) + os.sep + user + '-' + timestamp
    trial_dir = os.path.abspath(start) + os.sep + user + os.sep + timestamp
    #--------------------------------------------
    #                                    ^^^^^^
    #                                    ||||||
    # os.sep = '/' in unix, '\\' on windoze
    #--------------------------------------------

    # Make sure it's not a duplicate directory name
    k = 0
    while (k < number_of_tries and trial_dir in dir_listing):
        sleep(delay)
        timestamp = ctime(time())
        timestamp = timestamp.replace(' ', '_')
        trial_dir = os.path.abspath(start) + '/' + user + '-' + timestamp
        k = k + 1
    if (k == number_of_tries):
        print 'Unable to create the darn thing; you have a duplicate'
        publish_event("Unable to create subdirectory", topic = "FSP_log") 
    return trial_dir


"""
IOFileHandling
--------------
Utility Python code for reading in required list of input files and
checking for their presence, and to read a list of output files created
so that they can be announced and potentially archived
"""
import os, sys

#-------------------------------------------------------------------------
# The line returned from readlines will have a carriage return at the end,
# so strip it away via indexing [:-1]. This is like chomp in Perl.
#-------------------------------------------------------------------------
def Publish_outputList():
    try:
        output_dir = read_dict(filename = "SWIM_component_results")
        for key in output_dir.keys():
            action = output_dir[key]
            publish_event(message = key, topic = "FSP_data", action = action) 
        return
    except Exception, ex:
        print "exception in Publish_outputList: %s" %  ex

def Check_InputFiles():
    try:
        input_dir = read_dict(filename = "SWIM_component_required")
        for key in input_dir.keys():
            if (not os.path.isfile(os.getcwd() + '/' + key) ):
                message = 'Failed to find a required input file ' + key
                publish_event(message = message, topic = "FSP_log", action = "halt_run")
                print message
                return 0
        publish_event("All required input files found", topic = "FSP_data") 
    except: 
        message = 'No listing of required files (SWIM_component_required) is available'
        publish_event(message = message, topic = "FSP_log", action = "halt_run")
        print message
    return 1

#=========================================================================
def Populate_newdir(newdir):
    """ 
    -----------------------------------------------------------------------------
    Populate_newdir: 
        Create copies or links of required files into new subdirectory for a
        new run of this component. For the executable, make a link. 
    -----------------------------------------------------------------------------
    """ 
    import shutil, os
    # os.mkdir(newdir)
    os.makedirs(newdir)
    shutil.copy('SWIM_component_required', newdir + os.sep + 'SWIM_component_required') 
    # os.umask(022)  
    try:
        input_dir = read_dict(filename = "SWIM_files")
        for key in input_dir.keys():
            shutil.copy( key, newdir + os.sep + key) 
            shutil.copymode( key, newdir + os.sep + key) 
        input_dir = read_dict(filename = "SWIM_component_required")
        for key in input_dir.keys():
            shutil.copy( key, newdir + os.sep + key) 
            shutil.copymode( key, newdir + os.sep + key) 
    except:
        message = 'Unable to copy files in SWIM_component_required to working directory'
        publish_event(message = message, topic = "FSP_log", action = "halt_run")
        print message

#=========================================================================
def read_dict (conf_dict = {}, filename = "SWIM_config"):
    """

    Open and read a dictionary of key-value pairs from the file given by
    filename. Use the read-in values to augment or update the dictionary passed
    in, then return the new dictionary.

    """
    from utils import publish_event
    try:
        config_file = open(filename, "r")
        if config_file:
            line = config_file.readline().strip()
        else:
            line = ""
    except:
        message = "Unable to open config file " + filename
        publish_event(message, topic = FSP_log, action = "halt_run")
        print message
        raise IOError, "Unable to open config file in read_dict"
            
    try:
        while line:
            name, val = line.split("=")
            name = name.strip()
            val = val.strip()
            conf_dict[name] = val
            if config_file:
                line = config_file.readline().strip()
            else:
                line = ""
        config_file.close()
        return conf_dict
    except Exception, ex:
        print "Unable to augment conf_dict in read_dict: %s" % ex
        raise IOError, "Unable to augment conf_dict in read_dict"
            

