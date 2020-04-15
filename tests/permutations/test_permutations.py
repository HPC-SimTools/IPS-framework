#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
#from processing import Queue
import gc
import pprint
import sys
import socket
import getopt
import os
import traceback
import time
import unittest
import logging
import string
import subprocess
from test_parameterized_cases import ParameterizedTestCase

sys.path.append('..')
from frameworkpath import *
sys.path.append(fsrc)

from ips import Framework
from configobj import ConfigObj

class test_permutations(ParameterizedTestCase):

    def printUsageMessage(self):
        print('Usage: ips [--create-runspace | --run-setup | --run]+ --simulation=SIM_FILE_NAME --platform=PLATFORM_FILE_NAME --log=LOG_FILE_NAME [--debug | --ftb]')

    def setUp(self):
        if self.param == None:
            return
        print()
        print('------------------------------------------------------------------------------------')
        print('Parameterization for this test')
        print('Command   -  DO_CREATE_RUNSPACE   =', ("F","T")[self.param.do_create_runspace], end=' ')
        print('    DO_RUN_SETUP   =', ("F","T")[self.param.do_run_setup], end=' ')
        print('    DO_RUN   =', ("F","T")[self.param.do_run])
#       print 'Command   - DO_CREATE_RUNSPACE   = %s   DO_RUN_SETUP   = %s   DO_RUN   = %s' % \
#           (self.param.do_create_runspace, self.param.do_run_setup, self.param.do_run)
        print('Checklist -  CREATE_RUNSPACE_DONE =', ("F","T")[self.param.create_runspace_done], end=' ')
        print('    RUN_SETUP_DONE =', ("F","T")[self.param.run_setup_done], end=' ')
        print('    RUN_DONE =', ("F","T")[self.param.run_done])
#       print 'Checklist - CREATE_RUNSPACE_DONE = %s   RUN_SETUP_DONE = %s   RUN_DONE = %s' % \
#           (self.param.create_runspace_done, self.param.run_setup_done, self.param.run_done)
        print('------------------------------------------------------------------------------------')

    def test_given_parameters(self):

        if self.param == None:
            return
        # create the checklist.conf that Framework will use
#       checklist_file_name = os.path.join(self.fwk.sim_root, 'checklist.conf')


        sim_conf = ConfigObj(self.param.cfgFile_list[0], interpolation='template',
                         file_error=True)

        # try making the simulation root directory
        try: 
            os.makedirs(sim_conf['SIM_ROOT'])
        except OSError as xxx_todo_changeme:
            (errno, strerror) = xxx_todo_changeme.args
            if (errno != 17):
                self.services.exception('Error creating directory %s : %s' ,
                                        workdir, strerror)

        checklist_file_name = os.path.join(sim_conf['SIM_ROOT'], 'checklist.conf')
        checklist_file = open(checklist_file_name, 'w')
        if self.param.create_runspace_done:
            checklist_file.write('CREATE_RUNSPACE = DONE\n')
        else:
            checklist_file.write('CREATE_RUNSPACE = NOT_DONE\n')
        if self.param.run_setup_done:
            checklist_file.write('RUN_SETUP = DONE\n')
        else:
            checklist_file.write('RUN_SETUP = NOT_DONE\n')
        if self.param.run_done:
            checklist_file.write('RUN = DONE\n')
        else:
            checklist_file.write('RUN = NOT_DONE\n')
        checklist_file.flush()
        checklist_file.close()

        call_args = []
        call_args.append(fsrc + '/ips.py')
        if self.param.do_create_runspace:
            call_args.append('--create-runspace')
        if self.param.do_run_setup:
            call_args.append('--run-setup')
        if self.param.do_run:
            call_args.append('--run')
        
        cfg_files_str = '--simulation=' + self.param.cfgFile_list[0]
        for file in self.param.cfgFile_list[1:]:
            cfg_files_str += ',' + file
        call_args.append(cfg_files_str)

        if self.param.platform_filename:
           call_args.append('--platform=' + self.param.platform_filename)
        call_args.append('--log=' + self.param.log_file)

        print(string.join(call_args, ' '))
        #test must return true if nothing bad happened, false otherwise
#       self.assertTrue(self.fwk.run(), 'error in running fwk')
        self.assertEqual(subprocess.call(call_args), 0, 'error in running IPS')

        """
        # set correct result of CREATE_RUNSPACE parameterization
        if self.param.do_create_runspace or self.param.create_runspace_done:
            self.create_runspace_result = 'DONE'
        else:
            self.create_runspace_result = 'NOT_DONE'

        # set correct result of RUN_SETUP parameterization
        if self.param.do_run_setup and self.create_runspace_result == 'DONE':
            self.run_setup_result = 'DONE'
        elif self.param.run_setup_done and self.param.create_runspace_done:
            self.run_setup_result = 'DONE'
        elif self.param.run_setup_done and not self.param.do_create_runspace:
            self.run_setup_result = 'DONE'
        else:
            self.run_setup_result = 'NOT_DONE'
            
        # set correct result of RUN parameterization
        if self.param.do_run and self.run_setup_result == 'DONE':
            self.run_result = 'DONE'
        elif not self.param.do_run and self.param.run_done:
            self.run_result = 'NOT_DONE'
        else:
            self.run_result = 'NOT_DONE'
        """
        # If you create a runspace, it doesn't matter what was in the 
        # directory before it's now invalidated...
        if self.param.do_create_runspace:
            self.param.run_setup_done = False
            self.param.run_done = False

        # If you do run setup over a previous run, it invalidates the
        # run results because the inputs and outputs don't match now...
        if self.param.do_run_setup:
            self.param.run_done = False

        if self.param.do_create_runspace or self.param.create_runspace_done:
            self.create_runspace_result = 'DONE'
        else:
            self.create_runspace_result = 'NOT_DONE'

        if (self.param.do_run_setup or self.param.run_setup_done) and \
                    self.create_runspace_result == 'DONE':
            self.run_setup_result = 'DONE'
        else:
            self.run_setup_result = 'NOT_DONE'

        #  ((       T          or           F        ) and          F           ) and           T
        if ((self.param.do_run or self.param.run_done) and \
                    self.run_setup_result == 'DONE') and \
                    self.create_runspace_result == 'DONE':
            self.run_result = 'DONE'
        else:
            self.run_result = 'NOT_DONE'

        # read in the values the Framework wrote out
        self.conf = ConfigObj(checklist_file_name, 
                         interpolation = 'template',
                         file_error = True)

        self.assertEqual(self.create_runspace_result, self.conf['CREATE_RUNSPACE'])
        self.assertEqual(self.run_setup_result, self.conf['RUN_SETUP'])
        self.assertEqual(self.run_result, self.conf['RUN'])

