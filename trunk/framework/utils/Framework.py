#!/usr/bin/env python
"""
------------------------------------------------------------------------
Framework.py:
-------------
Generic component wrapper for the FSP project.  

initialize(): checks for the
existence of the needed input files as listed in the file "input_files",
creates a new subdirectory to launch the run, copies input files over
to it, announces the preliminary information about job, and then returns.

step(): user's component code is executed in the new subdirectory.

finalize():
Upon completion, finalize() announces the output files created,
listed in "output_files". 


    ----------------------------------
    IU Fusion Simulation Project Team:
    ----------------------------------
    Randall Bramley
    Joseph Cottam
    Anne Faber
    Samantha Foley
    Nisha Gupta
    Yu (Marie) Ma
    Yongquan (Cathy) Yuan

    Department of Computer Science
    Indiana University, Bloomington
------------------------------------------------------------------------
"""
import os, sys, shutil

#------------------------------------------------
# Local modules; need to make this less hardwired
#------------------------------------------------
baselocation = '/home/fsp/lsa/PythonUtils'
# baselocation = '/local/bramley/lsa/PythonUtils'
# jpypelocation = baselocation + os.sep + 'JPype-0.5.1/build/lib.linux-i686-2.4'
# jpypelocation = '/home/fsp/jpype/lib/python'
jpypelocation = '/home/fsp/jpype/lib/python'
sys.path.append(baselocation)
sys.path.append(jpypelocation)

#-----------------------------------------------------------------------
# Extreme laziness on my part: don't want to type quote marks around the
# topic each time I publish an event.
#-----------------------------------------------------------------------
FSP_data  = 'FSP_data'
FSP_job   = 'FSP_job'
FSP_log   = 'FSP_log'
FSP_debug = 'FSP_debug'

from utils import *
    
#----------------------------------------------------------------------------------
# Read "Services" as "Services provided by the component for the framework to use"
#----------------------------------------------------------------------------------
class Services:
    
    #---------------------------------------
    def initialize(self, program = 'Scale', debug = False):
    #---------------------------------------
    
        import os, sys, shutil
        from time import time, ctime  
        
        #--------------------------------------------------------------------
        # If the executable needed is not present, then run make to create it
        #--------------------------------------------------------------------
        
        fullcommand = os.getcwd() + os.sep + program 
        if not os.path.isfile(fullcommand):
            publish_event("Running make command for component " + program, topic = FSP_log)
            os.system('make')
            publish_event("Finished make command for program " + program, topic = FSP_log)
    
        if not os.path.isfile(fullcommand): # Make did not work, so give up
            publish_event("Unable to create executable for" + fullcommand, \
                           topic = "FSP_log")
            publish_event("You need to create the executable for " + program, \
                           topic = "FSP_log")
        else:
            #-------------------------------------
            # Prepare a subdir for the executable 
            #-------------------------------------
            present = Check_InputFiles()
            newdir = create_dir()
            if present:
                Populate_newdir(newdir)
                AddSysPath(newdir)
            else:
                publish_event("Required input file(s) missing for " + program, topic = "FSP_log")
                print 'Required input file(s) missing for ' , program
        #---------------------------------------------------------------------
        # Return directory so that the runit script can do further work in it.
        #---------------------------------------------------------------------
        return newdir 
    
    
    #-----------------------------------------------
    def step(self, program = 'Scale', subdir = '.', debug = False):
    #-----------------------------------------------
    
        import os, sys, shutil
        from time import time, ctime  
        #------------------------------------------------
        # Local modules; need to make this less hardwired
        #------------------------------------------------
        
        sys.path.append(baselocation)
        from utils import AddSysPath, publish_event, Publish_outputList
        try: 
            import batch_mgmt_script
            #from batch_mgmt_script import fsp_job
        except:
            print '*** Could not import batch manager'
            publish_event("Could not import batch manager", topic = "FSP_log")
        
        AddSysPath(subdir)
        os.chdir(subdir)
        #==================================================================================
        job = batch_mgmt_script.fsp_job()
        #job = fsp_job()
        job.submit_job(debug_on = debug)
        job.monitor_job(debug_on = debug)
        #==================================================================================
        # newcmd = subdir + os.sep + program
        # try:
        #     os.system(newcmd)
        #  except:
        #     print '*** Unable to run command ', newcmd
        #     publish_event("Unable to run " + program, topic = "FSP_log")
        #==================================================================================
        #-------------------------------------------------------------
        # Notify data manager about existence of output files from run
        # This assumes the execution created the file output_files
        #-------------------------------------------------------------
        Publish_outputList()
        return 
    
    #---------------------------------------------------
    def finalize(self, program = 'Scale', subdir = '.', debug = False):
    #---------------------------------------------------
    
        import os, sys, shutil
        from time import time, ctime  
    
        try:
            os.chdir(subdir)
            try:
                Publish_outputList()
            except:
                print '*** Unable to publish list of output files '
                publish_event("Unable to publish list of output files ", topic = "FSP_log")
        except:
            print '*** Unable to chdir to ', subdir
            publish_event("Unable to chdir to " + subdir, topic = "FSP_log")
    
