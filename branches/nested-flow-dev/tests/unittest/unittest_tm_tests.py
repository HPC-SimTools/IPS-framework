#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
import socket
import unittest
import logging, logging.handlers
sys.path.append('..')
from frameworkpath import *
sys.path.append(fsrc)
from resourceManager import *
from taskManager import *
from ipsExceptions import *
import messages
my_version = float(sys.version[:3])
if my_version < 2.6:
    import processing
else:
    import multiprocessing

class faux_fwk(object):
    def __init__(self, host):
        self.host = host
        self.component_id = 1
        logger = logging.getLogger('FRAMEWORK')
        logger = logging.getLogger("FRAMEWORK")
        logger.setLevel(logging.DEBUG)
        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter
        formatter = logging.Formatter("%(asctime)s %(name)-15s %(levelname)-8s %(message)s")
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        logger.addHandler(ch)
        #console = logging.StreamHandler()
        #console.setLevel(logging.DEBUG)
        # set a format which is simpler for console use
        #formatter = logging.Formatter("%(asctime)s %(name)-15s %(levelname)-8s %(message)s")
        # tell the handler to use this format
        #console.setFormatter(formatter)
        self.current_logger = logger
        # add the handler to the root logger
        #self.current_logger.addHandler(console)
        self.default_logger = self.current_logger

    def register_service_handler(self, thing1, thing2):
        pass

    def debug(self, *args):
        try:
            self.current_logger.debug(*args)
        except:
            print 'error in Framework.debug', args
            raise


class faux_comp_reg(object):
    def __init__(self):
        #put some fake component data in here for testing
        self.my_comps = {}
        if my_version < 2.6:
            self.my_comps['compA'] = processing.Queue(0)
            self.my_comps['compB'] = processing.Queue(0)
            self.my_comps['compC'] = processing.Queue(0)
            self.my_comps['compD'] = processing.Queue(0)
            self.my_comps['compE'] = processing.Queue(0)
        else:
            self.my_comps['compA'] = multiprocessing.Queue(0)
            self.my_comps['compB'] = multiprocessing.Queue(0)
            self.my_comps['compC'] = multiprocessing.Queue(0)
            self.my_comps['compD'] = multiprocessing.Queue(0)
            self.my_comps['compE'] = multiprocessing.Queue(0)


    def getComponentArtifact(self, comp, artifact):
        if comp in self.my_comps:
            return self.my_comps[comp]
        else:
            raise Exception("can't find artifact")


class faux_config_mgr(object):
    def __init__(self, mpirun, host):
        self.comp_reg = faux_comp_reg()
        self.mpirun = mpirun
        self.host = host

    def get_platform_parameter(self, param):
        if param == 'MPIRUN':
            return self.mpirun
        elif param == 'HOST':
            return self.host
        else:
            raise Exception('bad get_config_parameter call')


class tmTestCase(unittest.TestCase):
    def xsetUp(self):
        # if you ar not working on jaguar or viz/mhd, this will give you 10 dummy nodes
        host = socket.gethostname()
        self.ff = faux_fwk(host)
        self.fcm = faux_config_mgr('mpirun', host)
        self.test_rm = ResourceManager(self.ff)
        self.test_tm = TaskManager(self.ff)
        # override real component registry with test registry
        self.test_tm.comp_registry = self.fcm.comp_reg
        self.test_rm.initialize(None, None, None, self.fcm)
        self.test_tm.initialize(None, None, self.test_rm, self.fcm)

    def xtearDown(self):
        del self.test_tm
        del self.test_rm
        del self.fcm
        del self.ff

    def test_init_call(self):
        # Things that need to happen:
        #    - init call message is consumed - implied... no way to confirm
        #    - invocation message is created - check
        #    - invocation message is placed on the component's queue - check (well, it isn't empty)
        #    - call_id is generated - imbedded in above tests
        #    - call_id is returned - check
        # if you ar not working on jaguar or viz/mhd, this will give you 10 dummy nodes
        host = socket.gethostname()
        ff = faux_fwk(host)
        fcm = faux_config_mgr('mpirun', host)
        test_rm = ResourceManager(ff)
        test_tm = TaskManager(ff)
        # override real component registry with test registry
        test_tm.comp_registry = fcm.comp_reg
        test_rm.initialize(None, None, None, fcm)
        test_tm.initialize(None, None, test_rm, fcm)
        init_call_msg = messages.ServiceRequestMessage('driver',                  # calling component
                                                       test_tm.fwk.component_id,     # fwk
                                                       'compA',                   # called component
                                                       'step', None)              # method, args
        try:
            call_id = test_tm.init_call(init_call_msg)
        except Exception, e:
            self.fail(e.__str__())
        #print call_id
        #print self.test_tm.outstanding_calls
        print test_tm.comp_registry.my_comps['compA'].qsize()
        self.assertTrue(test_tm.outstanding_calls[call_id] == ('driver', None))
        self.assertTrue(test_tm.comp_registry.my_comps['compA'].qsize() == 1)


    def test_wait_call(self):
        """
        Check to see if the call completed.  If it has finished successfully,
        return the results.  If it has finished with an error, throw that error
        to the next level.  If the call has not completed, come back later.
        """
                # if you ar not working on jaguar or viz/mhd, this will give you 10 dummy nodes
        host = socket.gethostname()
        ff = faux_fwk(host)
        fcm = faux_config_mgr('mpirun', host)
        test_rm = ResourceManager(ff)
        test_tm = TaskManager(ff)
        # override real component registry with test registry
        test_tm.comp_registry = fcm.comp_reg
        test_rm.initialize(None, None, None, fcm)
        test_tm.initialize(None, None, test_rm, fcm)
        init_call_msg = messages.ServiceRequestMessage('driver',                  # calling component
                                                       test_tm.fwk.component_id,     # fwk
                                                       'compA',                   # called component
                                                       'step', 'sleep(0)')              # method, args
        try:
            call_id = test_tm.init_call(init_call_msg)
        except Exception, e:
            print e
            self.fail()
        #print call_id
        #print self.test_tm.outstanding_calls
        print test_tm.comp_registry.my_comps['compA'].qsize()
        self.assertTrue(test_tm.outstanding_calls[call_id] == ('driver', None))
        self.assertTrue(test_tm.comp_registry.my_comps['compA'].qsize() == 1)

        # simulate component actions and task launch
        m = test_tm.comp_registry.my_comps['compA'].get()
        # invoke message contains: fwk compID (sender), callee ID (recvr), method, args
        print m
        #----------------------------------------
        #   call completed and successful
        #----------------------------------------
        # ************  i think i may be using the wrong message types... the call_id and blocking value are in the wrong spots
        ccas_msg_blocking = messages.ServiceRequestMessage('driver',                          # calling component
                                                           test_tm.fwk.component_id,          # fwk
                                                           test_tm.fwk.component_id,          # ??????
                                                           'wait_call',                       # ???????
                                                           call_id, True)                     # call_id, blocking?
        ccas_msg_nonblocking = messages.ServiceRequestMessage('driver',                          # calling component
                                                              test_tm.fwk.component_id,          # fwk
                                                              test_tm.fwk.component_id,          # ??????
                                                              'wait_call',                       # ???????
                                                              call_id, False)                     # call_id, blocking?
        response_failure = messages.ServiceResponseMessage(test_tm.fwk.component_id,
                                                           'compA',
                                                           call_id,
                                                           messages.Message.FAILURE,
                                                           'something bad happened')
        response_success = messages.ServiceResponseMessage(test_tm.fwk.component_id,
                                                           'compA',
                                                           call_id,
                                                           messages.Message.SUCCESS,
                                                           5)
        print 'made messages'
        test_tm.finished_calls[call_id] = ('driver', response_success)
        print ccas_msg_blocking.args
        try:
            retval = test_tm.wait_call(ccas_msg_blocking)
        except Exception, e:
            print e
            self.fail()

        #----------------------------------------
        #   call completed and errors occured
        #----------------------------------------
        test_tm.finished_calls[call_id] = ('driver', response_failure)
        try:
            retval = test_tm.wait_call(ccas_msg_blocking)
        except Exception, e:
            print e
            # make sure the proper exception was thrown
            #self.fail()


        #----------------------------------------
        #   call not completed and blocking
        #----------------------------------------
        test_tm.finished_calls[call_id] = ('driver', None)
        try:
            retval = test_tm.wait_call(ccas_msg_blocking)
        except Exception, e:
            print e
            # make sure the proper exception was thrown
            #self.fail()

        #----------------------------------------
        #   call not completed and non-blocking
        #----------------------------------------
        test_tm.finished_calls[call_id] = ('driver', None)
        try:
            retval = test_tm.wait_call(ccas_msg_nonblocking)
        except Exception, e:
            print e
            # make sure the proper exception was thrown
            #self.fail()

    """

    def test_return_call(self):
        pass
    def test_init_task(self):
        pass
    def test_launch_task(self):
        pass
    def test_finish_task(self):
        pass
    """
if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(tmTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
