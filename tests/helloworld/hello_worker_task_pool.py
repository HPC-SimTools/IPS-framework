#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------

from  component import Component
from  numpy import random
import os
import sys

class HelloWorker(Component):
    def __init__(self, services, config):
        Component.__init__(self, services, config)
        print 'Created %s' % (self.__class__)

    def init(self, timeStamp=0.0):
        return

    def step(self, timeStamp=0.0):
        random.seed(1)
        print 'Hello from HelloWorker'
        duration = random.random_integers(1, high=10, size=100)
        tasks = {}
        bin = '/bin/sleep' 
        cwd = self.services.get_working_dir()
        pool = self.services.create_task_pool('pool')
        for i in range(100):
            self.services.add_task('pool', 'task_'+str(i), 1, cwd, bin, str(duration[i]))
        ret_val = self.services.submit_tasks('pool')
        print 'ret_val = ', ret_val
        exit_status = self.services.get_finished_tasks('pool')
        print exit_status
        
        print "====== Non Blocking "
        for i in range(100):
            self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, bin, str(duration[i]))
        total_tasks = 100
        active_tasks = self.services.submit_tasks('pool', block=False)
        finished_tasks = 0
        while (finished_tasks <  total_tasks) :
            exit_status = self.services.get_finished_tasks('pool')
            print exit_status
            finished_tasks += len(exit_status)
            active_tasks -= len(exit_status)
            print 'Active = ', active_tasks, 'Finished = ', finished_tasks
#            if (finished_tasks >= 50):
#                self.services.remove_task_pool('pool')
#                break
            if (active_tasks + finished_tasks < total_tasks):
                new_active_tasks = self.services.submit_tasks('pool', block=False)
                active_tasks += new_active_tasks
                print 'Active = ', active_tasks, 'Finished = ', finished_tasks

        print "====== Non Blocking  2 "
        for i in range(50):
            self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, bin, str(duration[i]))
        total_tasks = 50
        active_tasks = self.services.submit_tasks('pool', block=False)
        finished_tasks = 0
        while (finished_tasks <  total_tasks) :
            exit_status = self.services.get_finished_tasks('pool')
            print exit_status
            finished_tasks += len(exit_status)
            active_tasks -= len(exit_status)
            if (i < 99):
                i += 1
                self.services.add_task('pool', 'Nonblock_task_'+str(i), 1, cwd, bin, str(duration[i]))
                total_tasks +=1
            print 'Active = ', active_tasks, 'Finished = ', finished_tasks, 'Total = ', total_tasks
#            if (finished_tasks >= 50):
#                self.services.remove_task_pool('pool')
#                break
            if (active_tasks + finished_tasks < total_tasks):
                new_active_tasks = self.services.submit_tasks('pool', block=False)
                active_tasks += new_active_tasks
                print 'Active = ', active_tasks, 'Finished = ', finished_tasks

            
            
        return
    
    def finalize(self, timeStamp=0.0):
        return
    
