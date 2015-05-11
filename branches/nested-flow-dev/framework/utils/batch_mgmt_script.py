#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
"""

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
    [bramley,jcottam,anmcleve,ssfoley,nigupta,yuma,yyuan]@cs.indiana.edu


this version uses the subprocess module

this script needs to:
 - submit jobs to batch manager (SLURM, PBS, or None ~ no batch manager... just run)
 - monitor queue and publish status events
 - remove jobs from queue
 - kill a job when it is running (Ctrl+C)

there will be a config file where the paramaters for running the job are located.
(i.e. - batch manager, number of nodes/processors, ???)
The config file will have the following format:
<name of script to run>
<batch manager name or None>
<number of nodes>
<"True" if MPI job, "False" otherwise>

---------------------------------------------------------------------
Our states: (see file "states" for more info)
---------------------------------------------------------------------

  Ours  |  SLURM  |      PBS      |  PROCS
--------------------------------------------
  done  |  CD,TO  |   E           |  X,Z
 trans  |   CG    |   T           |  T
 failed |  F,NF   |               |
waiting |   PD    |   Q, W, S, H  |  W,S,D
running |   R     |   R           |  R

"""

import sys
import os
import time
import subprocess as sp
import Events

SLURM_STATES = {"CD":"done", "TO":"done", "CG":"trans", "F":"failed", "NF":"failed",\
                "PD":"waiting", "R":"running"}
PROC_STATES = {"X":"done", "Z":"done", "T":"trans", "W":"waiting", "S":"waiting", \
               "D":"waiting", "R":"running"}
PBS_STATES = {"E":"done", "T":"trans", "Q":"waiting", "S":"waiting", "W":"waiting", \
              "H":"waiting", "R":"running"}

class fsp_job:   #our new job class
    #my_vals is a dictionary that contains the configuration information as read from the config file
    my_vals = { "batch_mgr" : "",
                "num_nodes" : 1,
                "executable" : "hostname",
                "jobid" : "0",
                "status" : "done",
                "mpi_job" : False,
                "Jpype" : "/usr/bin",
                "event_channel" : "shortly.cs.indiana.edu:12345",
                "utilpath" : "."
                }

    def parse_config (self):
        try:
            config_file = open("SWIM_config", "r")  #assuming that config is in the current dir

            if config_file:
                line = config_file.readline().strip()
            else:
                line = ""

            while line:
                name, val = line.split("=")
                name = name.strip()
                val = val.strip()
                if self.my_vals.has_key(name):
                    if name == "num_nodes":
                        self.my_vals[name] = int(val)
                    elif name == "mpi_job":
                        self.my_vals[name] = bool(val)
                    elif name == "Jpype":
                        self.my_vals[name] = os.path.expanduser(val)
                    else:
                        self.my_vals[name] = val
                else:
                    print "unrecognized name in name-value pair: %s = %s\n" % (name, val)
                if config_file:
                    line = config_file.readline().strip()
                else:
                    line = ""

            config_file.close()
        except Exception, ex:
            print "problems parsing config file: %s" % ex


    #states = something.... see notes above
    def submit_job(self, debug_on = False):
        #submits job to batch_mgr, if there is one present
        try:
            if self.my_vals["batch_mgr"] == "SLURM":
                if self.my_vals["mpi_job"]:
                    # "sam_run" calls mpi_run.py if it is an mpi job
                    cmd = "srun -N %d -b sam_run" % self.my_vals["num_nodes"]
                else:
                    #grab nodes, run, and grab stderr to get the jobid
                    cmd = "srun -N %d -b %s" % (self.my_vals["num_nodes"], \
                           self.my_vals["executable"])   #assume it has ./ if needed

                #using subprocess
                p1 = sp.Popen(cmd, shell=True, stderr=sp.PIPE)
                s = p1.stderr.read()
                g = s.split()
                self.my_vals["jobid"] = g[2]
                self.my_vals["status"] = g[3]

            elif self.my_vals["batch_mgr"] == "PBS":
                scriptfile = open("scriptfile", "w")
                scriptfile.write("#!/bin/tcsh\n")
                scriptfile.write("#PBS -l ncpus=" + str(self.my_vals["num_nodes"]) + "\n")
                scriptfile.write("#PBS -l walltime=00:05:00\n")
                scriptfile.write("#PBS -l mem=50mb\n")
                scriptfile.write("#PBS -r n\n")
                scriptfile.write("#PBS -N FSPjobname\n")
                scriptfile.write("#PBS -q sgi\n")
                scriptfile.write("#PBS -V\n")
                scriptfile.write("cd " + os.getcwd() + "\n")
                scriptfile.write(self.my_vals["executable"] + "\n")
                scriptfile.close()
                #cmd = "qsub -l nodes=" + self.my_vals["num_nodes"] + " scriptfile"
                cmd = "qsub scriptfile"
                os.system("pwd")
                p1 = sp.Popen(cmd, shell=True, stderr=sp.PIPE, stdout=sp.PIPE)
                s = p1.stdout.read()
                g = s.split(".")
                self.my_vals["jobid"] = g[0]

            else:
                #just run
                # need to get pid... storing it in jobid should be fine
                cmd = self.my_vals["executable"]

                #new version using subprocess
                #print "starting the script"
                p1 = sp.Popen(cmd, shell=True)
                #print "done running script"
                self.my_vals["jobid"] = str(p1.pid)

            if debug_on:
                print cmd
                print "my jobid is: %s" % self.my_vals["jobid"]

            message = "job %s started" % self.my_vals["jobid"]
            Events.publish_event(message, topic='FSP_job')
        except Exception, ex:
            print "submit_job failed with exception %s" % ex

    def monitor_job(self, interval=1, debug_on = False):
        #checks the status of the job
        try:

            if self.my_vals["batch_mgr"] == "SLURM":
                #this command will get the status and cputime ( -o \" %.2t %.10M\")
                #of just self.my_vals["jobid"] (-j self.my_vals["jobid"]) without the heading (-h)
                cmd = "squeue -j " + self.my_vals["jobid"] + " -h -o \" %.2t %.10M\" "

                #new: the squeue command prints to stdout and stderr
                #extract status from output
                p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
                out = p1.stdout.read()
                while out:
                    s, t = out.split()
                    s = s.strip()
                    t = t.strip()
                    self.my_vals["status"] = SLURM_STATES[s]
                    message = "The status of job %s is %s. -- The cpu time is %s."  % (self.my_vals["jobid"], self.my_vals["status"], t)
                    if debug_on:
                        print "monitor:\n" + message
                    Events.publish_event(message,topic='FSP_job')
                    time.sleep(interval)
                    p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
                    out = p1.stdout.read()

            elif self.my_vals["batch_mgr"] == "PBS":
                cmd = "qstat -r %s" % self.my_vals["jobid"]
                #                                                            Req'd  Req'd   Elap
                #Job ID          Username Queue    Jobname    SessID NDS TSK Memory Time  S Time
                #--------------- -------- -------- ---------- ------ --- --- ------ ----- - -----
                #126437.aviss.av huili    iq       hu-full-6    3730  80 160    --  11:39 R 00:02

                #extract status from output
                p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
                out = p1.stdout.read()
                while out:
                    lines = out.split("\n")
                    info = lines[5].split()
                    s, t = info[9], info[10]
                    s = s.strip()
                    t = t.strip()
                    self.my_vals["status"] = PBS_STATES[s]
                    message = "The status of job %s is %s. -- The cpu time is %s."  % (self.my_vals["jobid"], self.my_vals["status"], t)
                    if debug_on:
                        print "monitor:\n" + message
                    Events.publish_event(message,topic='FSP_job')
                    time.sleep(interval)
                    p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
                    out = p1.stdout.read()

            else:
                #this command will get the status and cputime ( -o s,cputime)
                #of just self.my_vals["jobid"] (--pid self.my_vals["jobid"]) without the heading (--no-heading)
                cmd = "ps -o s,cputime --pid %s --no-heading" %  self.my_vals["jobid"]

                #extract status from output
                p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
                out = p1.stdout.read()
                while out:
                    s, t = out.split()
                    s = s.strip()
                    t = t.strip()
                    self.my_vals["status"] = PROC_STATES[s[0]]
                    message = "The status of job %s is %s. -- The cpu time is %s."  % (self.my_vals["jobid"], self.my_vals["status"], t)
                    if debug_on:
                        print "monitor:\n" + message
                    Events.publish_event(message,topic='FSP_job')
                    time.sleep(interval)
                    p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
                    out = p1.stdout.read()

            self.my_vals["status"] = "done"
            message = "The status of job %s is %s." % (self.my_vals["jobid"], self.my_vals["status"])
            if debug_on:
                print "monitor:\n" + message
            Events.publish_event(message,topic='FSP_job')
        except Exception, ex:
            print "monitor_job failed with exception %s" % ex

    def remove_from_q(self, debug_on = False):
        #removes the job from the queue
        # scancel for SLURM, and qdel for PBS
        # scancel and qdel will remove the job from the queue if waiting
        try:
            if self.my_vals["batch_mgr"] == "SLURM":
                cmd = "scancel " + self.my_vals["jobid"]
            elif self.my_vals["batch_mgr"] == "PBS":
                cmd = "qdel " + self.my_vals["jobid"]
            else:
                #kill -9
                cmd = "kill -9 " + self.my_vals["jobid"]
                os.system(cmd)
                cmd = "ps -f -p " + self.my_vals["jobid"]

            p1 = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            out = p1.stdout.read()
            message = out
            if debug_on:
                print "rfq:\n" + out
            Events.publish_event(message,topic='FSP_job')
        except Exception, ex:
            print "remove_from_q failed with exception %s" % ex

    def kill_job(self, debug_on = False):
        #kills a running job -- which is exactly what remove from queue does
        self.remove_from_q(debug_on)

    def __init__(self):
        #gets the info from the config file
        self.parse_config()

        #set the path to Jpype
        sys.path.append(self.my_vals["Jpype"])

        try:
            Events.set_default_broker(self.my_vals["event_channel"])
        except Exception, ex:
            print "events not working: %s" % ex

if __name__ == "__main__":
    my_job = fsp_job()

    my_job.submit_job()
    time.sleep(2)
    my_job.monitor_job(0.5)
    time.sleep(2)
    my_job.kill_job()
