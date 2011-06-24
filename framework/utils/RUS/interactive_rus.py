'''
Resource Usage Simulator (RUS)
------------------------------

by Samantha Foley, Indiana University
3/4/2010

This RUS simulates the resource usage of a MCMD application as described 
by the input files.  It is a tool that helps to determine what resource 
allocation algorithms and component configurations work best for classes 
of applications.
'''

import sys, os
import getopt
from configobj import ConfigObj
from time import gmtime, strftime, asctime, time
from resource_manager import resource_mgr
from simulation import simulation
from component import component
import subprocess
#from random import shuffle
import random
#import argparse # <----- this only works in python 2.7
#import matplotlib
#matplotlib.use('AGG')
import matplotlib.pyplot as plt



comment_symbol = '%' # % in matlab, # in python, // in c/c++, ! in fortran

class framework():
    def __init__(self):
        self.simulations = list()
        self.beginning_of_time = strftime("%d_%b_%Y-%H.%M.%S", gmtime())
        self.today, self.now = self.beginning_of_time.split('-') # puts the date in self.today and the time in self.now
        self.log_types = {}
        self.curr_time = 0
        self.fwk_global_time = 0
        self.comment_symbol = '#'
        self.total_usage = 0
        self.usage_times = list()
        self.usage_vals = list()


        #-----------------------------------------
        #   get command line options
        #-----------------------------------------
        """
        parser = argparse.ArgumentParser(description="Simulate resource usage over time for a given set of simulations on a given allocation.")
        parser.add_argument('--resource', nargs=1, action="store", type=argparse.FileType('r'), help="description of the architecture and allocation in which to simulate execution")
        parser.add_argument('--config', nargs='+', action="append", type=argparse.FileType('r'), help="the config file(s) describing the simulations to be analyzed")
        parser.add_argument('--mapfile', nargs=1, action="store", type=argparse.FileType('r'), help="a list of the state descriptions and values to be used")
        parser.add_argument('--log', nargs='?', action="store", type=string, help = "optional log file prefix")

        args = parser.parse_args()
        print args
        print resource
        print config
        print mapfile
        print log
        return

        """ 
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'r:m:c:l:s:', ['resource=','config=','mapfile=','log=','seed='])
        except getopt.GetoptError, err:
            # print help information and exit:
            print str(err) # will print something like "option -a not recognized"
            usage()
            sys.exit(2)

        self.lfname = 'log'
        self.rlfname = 'log.readable'
        self.ltm = 'logTypeMap'
        cfname = ''
        self.config_files = list()

        try:
            for o,a in opts:
                if o == '-m' or o == '--mapfile':
                    self.ltm = a
                elif o == '-c' or o == '--config':
                    self.config_files.append(a)
                elif o == '-l' or o == '--log':
                    self.lfname = a
                    self.rlfname = a + '.readable'
                elif o == '-r' or o == '--resource':
                    self.resource_file = a
                elif o == '-s' or o =='--seed':
                    self.myseed = int(a)
                else:
                    print 'bad input'
                    usage()
        except:
            print 'problems getting the command line args'
            raise
        
        try:
            print self.myseed,
        except:
            self.myseed = int(time())
            print self.myseed,
        self.my_rand = random.Random()
        self.my_rand.seed(self.myseed)        


        #-----------------------------------------
        #   construct log files
        #-----------------------------------------
        try:
            self.create_logfiles()
        except:
            print "problems creating log files"
            raise

        #-----------------------------------------
        #   set up resource manager
        #-----------------------------------------
        try:
            self.RM = resource_mgr(self, self.resource_file)
        except:
            print "problems initializing the resource manager"
            raise

        #-----------------------------------------
        #    parse configuration 
        #-----------------------------------------
        try:
            self.parse_config(self.config_files)
        except:
            print "problems reading config file"
            raise

        #-----------------------------------------
        #   sim and comp maps
        #-----------------------------------------
        try:
            self.setup_logfiles()
        except:
            print "problems setting up sim, comp and log type maps"
            raise
            
        #----------------------------------------
        #   check data
        #----------------------------------------
        #for s in self.simulations:
        #    for c in s.my_comps.values():
        #        c.print_me()
                
    def create_logfiles(self):
        """
        this function will create the logging files
        """
        
        try:
            os.mkdir(self.today)
        except:
            pass
        t = self.now
        head, rtail = os.path.split(self.resource_file)
        #self.lfname = self.today + '/' + self.lfname + '.' + t
        self.rlfname = self.today + '/' + self.rlfname + '.' + t
        self.rufname = self.today + '/' + 'rwfile' + '.' + t + '-' + rtail
                        
        #self.logFile = open(self.lfname, 'w')
        self.rlogFile = open(self.rlfname, 'w')
        self.raw_usage = open(self.rufname, 'w')
        
        #pass
        
    def setup_logfiles(self):
        """
        set up the front matter for the logging files, and construct and record maps
        """
        #----------------------------------------
        # read logTypes into dictionary
        #----------------------------------------
        self.logTypeMap = open(self.ltm, 'r')
        logInfo = self.logTypeMap.readlines()
        for line in logInfo:
            if line:
                a = line.split()
                self.log_types.update({a[0]:int(a[1])})
        self.logTypeMap.close()

        #----------------------------------------
        # create simulation and component maps
        #----------------------------------------
        self.sim_map = dict()
        self.comp_map = dict()
        scount = 1
        ccount = 1
        self.sim_map.update({'None':0})
        for s in self.simulations:
            self.sim_map.update({s.name:scount})
            self.comp_map.update({s.name + '_' + 'None':0})
            for c in s.my_comps.values():
                self.comp_map.update({s.name + '_' + c.name:ccount})
                ccount = ccount + 1
            scount = scount + 1
        
        #----------------------------------------
        # write out simulation and component maps
        #----------------------------------------
        """
        for c in self.config_files:
            head, tail = os.path.split(c)
            map_file = open('sim_map' + tail, 'w')
            print >> map_file, 'simulation map:'
            for k,v in self.sim_map.items():
                print >> map_file, k, v
            print >> map_file, 'component map:'
            for k,v in self.comp_map.items():
                print >> map_file, k, v
            map_file.close()
        """
        #----------------------------------------
        # write some header info
        #----------------------------------------
        
        allocated, total = self.RM.get_curr_usage()
        #print >> self.logFile, comment_symbol, 'The following data is associated with the run executed at', self.beginning_of_time
        print >> self.rlogFile, comment_symbol, 'The following data is associated with the run executed at', self.beginning_of_time
        #print >> self.logFile, comment_symbol, 'On host', os.uname()[1], 'with configuration files:' #self.config_file, self.resource_file
        print >> self.rlogFile, comment_symbol, 'On host', os.uname()[1], 'with configuration files:' #self.config_file, self.resource_file
        for c in self.config_files:
            #print >> self.logFile, comment_symbol, c
            print >> self.rlogFile, comment_symbol, c
        #print >> self.logFile, comment_symbol, self.resource_file
        print >> self.rlogFile, comment_symbol, self.resource_file
        #print >> self.logFile, comment_symbol, '================================================================='
        print >> self.rlogFile, comment_symbol, '================================================================='
        self.logEvent(None, None, 'start_sim', "starting simulation")
        
    #-----------------------------------------------------------------------------------------------------
    #   logging functions:
    #     <global time> <sim> <component> <event type> <allocated nodes> <total nodes> <comment symbol> <comment>
    #         fwk         (------ caller -------)          (--------- RM --------)           fwk            caller
    #-----------------------------------------------------------------------------------------------------
            
    def logEvent(self, sim, comp, ltype, msg):
        
        allocated, total = self.RM.get_curr_usage()
        percent = 100 * (allocated / (float(total)))
        if not sim:
            s = 'None'
        else:
            s = sim
        if not comp:
            c = 'None'
        else:
            c = comp
            
        if s == 'None' and c == 'None':
            #print >> self.logFile, self.fwk_global_time, 0, 0, self.log_types[ltype], allocated, total, self.comment_symbol, msg
            print >> self.rlogFile, self.fwk_global_time, 'fwk', '---' , ltype, percent, '%  ', allocated, total, self.comment_symbol, msg
        elif c == 'None':
            #print >> self.logFile, self.fwk_global_time, self.sim_map[s], self.comp_map[s + '_' + c], self.log_types[ltype], percent, '%  ',allocated, total, self.comment_symbol, msg
            print >> self.rlogFile, self.fwk_global_time, sim, '---', ltype, percent, '%  ',allocated, total, self.comment_symbol, msg
        else:    
            #print >> self.logFile, self.fwk_global_time, self.sim_map[s], self.comp_map[s + '_' + c], self.log_types[ltype], percent, '%  ', allocated, total, self.comment_symbol, msg
            print >> self.rlogFile, self.fwk_global_time, sim, comp, ltype, percent, '%  ', allocated, total, self.comment_symbol, msg
        #print >> self.raw_usage, self.fwk_global_time, ' ', percent
        
        #pass

    def rw_log(self):
        #"""
        allocated, total = self.RM.get_curr_usage()
        percent = 100 * (allocated / (float(total)))
        self.usage_times.append(self.fwk_global_time)
        self.usage_vals.append(percent)
        print >> self.raw_usage, self.fwk_global_time, ' ', percent
        #"""
        #pass

    def parse_config(self, conf_files):
        #----------------------------------------
        # read and parse config file 
        # of simulations and components
        #----------------------------------------
        for conf_file in conf_files:
            try:
                config = ConfigObj(conf_file, file_error=True, interpolation='template')
            except IOError, (ex):
                print 'Error opening/finding config file %s' % conf_file
                print 'ConfigObj error message: ', ex
                raise
            except SyntaxError, (ex):
                print 'Syntax problem in config file %s' % conf_file
                print 'ConfigObj error message: ', ex
                raise
        
            try:
                sims = config['simulation']
                if not isinstance(sims, list):
                    sims = [sims]
                for s in sims:
                    self.simulations.append(simulation(config[s], self, len(self.simulations)))
                self.description = config['description']
            except:
                print 'problem parsing simulations'
                raise

    def go(self):
        sims = self.simulations
        self.fwk_global_time = 0
        # simulation start up time taken into account....
        num_sims = len(sims)
        ready = []
        running = []
        blocked = []
        to_run = []
        #--------------------------------------------
        #  execute simulations
        #--------------------------------------------

        for s in sims:
            to_run.extend(s.get_ready_comps())
        print 'length of sims:', len(sims)
        print 'length of to_run:', len(to_run)

        #print [k.name for k in to_run]
        while sims:
            min_update_time = 0
            running = []
            #ready = []
            # NEED TO FIX
            #get running comps
            for s in sims:
                running.extend(s.get_running_comps())
            
            #run ready comps
            #self.my_rand.shuffle(ready)
            for c in to_run:
                c.run()
                if c.state == "running":
                    running.append(c)

            for c in running:
                try:
                    to_run.remove(c)
                except:
                    pass

            self.rw_log()
            #let sims incorporate newly running comps
            for s in sims:
                s.update_resource_info()
            
            #log resource usage for current global time
            print 'to_run:', [k.name for k in to_run]
            print 'running:', [k.name for k in running]        
            #find update time
            #print 'about to update time'
            try:
                min_update_time = running[0].curr_exec_time
                for c in running:
                    if c.curr_exec_time < min_update_time:
                        min_update_time = c.curr_exec_time
            except:
                print 'not enough nodes to run tasks'
                #self.logFile.close()
                self.rlogFile.close()
                #self.raw_usage.close()
                #subprocess.call(['rm', self.lfname, self.rlfname, self.rufname])
                raise 

            self.rw_log()
            #update all with update time
            self.fwk_global_time += min_update_time
            for s in sims:
                finished_comps, nctr = s.sync(min_update_time)
                print 'added comps:', nctr
                print 'finished comps:', finished_comps
                # add next comps to run to to_run list
                for c in nctr:
                    to_run.append(c)
                #if finished_comps:
                #    for c in finished_comps:
                if s.is_done:
                    self.total_usage += s.report_usage()
                    sims.remove(s)
        self.rw_log()
        self.logEvent(None, None, 'end_sim', "end of simulation")
        #for s in self.simulations:
        #    self.total_usage += s.report_usage()
        
        confs = "config files: " + self.config_files[0]
        for c in self.config_files[1:]:
            confs = confs + ", " + c
        confs = confs + " -- "
        #h, conf = os.path.split(self.config_file)
        h, res = os.path.split(self.resource_file)
        cpuhrs_charged = (self.RM.nodes * self.RM.ppn * self.fwk_global_time) / 3600.0
        cpuhrs_used = self.total_usage / 3600.0
        efficiency = cpuhrs_used / cpuhrs_charged
        # print the config file name, nodes, ppn, total time, CPU hours
        #print confs,  self.RM.nodes, 'nodes,', self.RM.ppn, 'ppn,' , self.fwk_global_time, 'seconds,', (self.RM.nodes * self.RM.ppn * self.fwk_global_time) / 3600.0, 'CPU hours'
        print self.fwk_global_time, cpuhrs_charged, cpuhrs_used, efficiency

    def crunch(self):
        """
        uses maptplotlib to graph the usage over time
        """
        plt.figure()
        plt.plot(self.usage_times[1:], self.usage_vals[:(len(self.usage_vals) - 1)], 'r')
        plt.ylim([0, 110])
        plt.show()

# end of framework

def usage():
    print "This script will simulate resource usage over time of a simulation."
    print "Please use the following options:"
    print "   -c, --config : file containing component information"
    print "   -m, --mapfile : file containing valid states and an explanation of what they mean"
    print "   -l, --log : log file location, default is log.<config file name>_<num procs>"
    print "   -r, --resource : file containing resource info"

if __name__ == "__main__":
    my_fwk = framework()
    my_fwk.go()
    my_fwk.crunch()
    sys.exit(0)

"""
random thoughts

think about using sets (as they are unordered)

logging resource data:
 - toplevel log can have framework and simulation resource usage
 - simulation log can have simulation and component resource usage
 - component log can have component resource usage with more detailed event information
"""
