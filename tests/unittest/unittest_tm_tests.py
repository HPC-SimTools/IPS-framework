# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import pytest
import socket
import logging
import logging.handlers
from ipsframework import ResourceManager
from ipsframework import TaskManager
from ipsframework import messages
from ipsframework.ipsExceptions import BlockedMessageException, IncompleteCallException
import multiprocessing


class faux_fwk:
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
        # console = logging.StreamHandler()
        # console.setLevel(logging.DEBUG)
        # set a format which is simpler for console use
        # formatter = logging.Formatter("%(asctime)s %(name)-15s %(levelname)-8s %(message)s")
        # tell the handler to use this format
        # console.setFormatter(formatter)
        self.current_logger = logger
        # add the handler to the root logger
        # self.current_logger.addHandler(console)
        self.default_logger = self.current_logger

    def register_service_handler(self, thing1, thing2):
        pass

    def debug(self, *args):
        try:
            self.current_logger.debug(*args)
        except Exception:
            print('error in Framework.debug', args)
            raise

    def warning(self, *args):
        try:
            self.current_logger.warning(*args)
        except Exception:
            print('error in Framework.warning', args)
            raise


class faux_comp_reg:
    def __init__(self):
        # put some fake component data in here for testing
        self.my_comps = {}
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


class faux_config_mgr:
    class faux_comp:
        sim_root = "test_sim_root"
    sim_map = {"test_sim": faux_comp()}
    fwk_sim_name = "test_sim"

    def __init__(self, mpirun, host):
        self.comp_reg = faux_comp_reg()
        self.mpirun = mpirun
        self.host = host

    def get_platform_parameter(self, param, silent=False):
        if param == 'MPIRUN':
            return self.mpirun
        elif param == 'HOST':
            return self.host
        elif param == 'NODE_ALLOCATION_MODE':
            return "shared"
        elif param == 'NODE_DETECTION':
            return "manual"
        elif param == 'NODES':
            return 1
        elif param == 'PROCS_PER_NODE':
            return 2
        elif param == 'TOTAL_PROCS':
            return 2
        elif param == 'CORES_PER_NODE':
            return 2
        elif param == 'SOCKETS_PER_NODE':
            return 1
        else:
            if not silent:
                raise Exception('bad get_config_parameter call')
            else:
                return None


class TestTmCase:

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
        test_rm.initialize(None, test_tm, fcm, False)
        test_tm.initialize(None, test_rm, fcm, False)
        init_call_msg = messages.ServiceRequestMessage('driver',                  # calling component
                                                       test_tm.fwk.component_id,     # fwk
                                                       'compA',                   # called component
                                                       'step', None)              # method, args
        call_id = test_tm.init_call(init_call_msg)
        print(test_tm.comp_registry.my_comps['compA'].qsize())
        assert test_tm.outstanding_calls[call_id] == ('driver', None)
        assert test_tm.comp_registry.my_comps['compA'].qsize() == 1

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
        test_rm.initialize(None, test_tm, fcm, False)
        test_tm.initialize(None, test_rm, fcm, False)
        init_call_msg = messages.ServiceRequestMessage('driver',                  # calling component
                                                       test_tm.fwk.component_id,     # fwk
                                                       'compA',                   # called component
                                                       'step', 'sleep(0)')              # method, args
        call_id = test_tm.init_call(init_call_msg)
        print(test_tm.comp_registry.my_comps['compA'].qsize())
        assert test_tm.outstanding_calls[call_id] == ('driver', None)
        assert test_tm.comp_registry.my_comps['compA'].qsize() == 1

        # simulate component actions and task launch
        m = test_tm.comp_registry.my_comps['compA'].get()
        # invoke message contains: fwk compID (sender), callee ID (recvr), method, args
        print(m)
        # ----------------------------------------
        #   call completed and successful
        # ----------------------------------------
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
        print('made messages')
        test_tm.finished_calls[call_id] = ('driver', response_success)
        print(ccas_msg_blocking.args)
        test_tm.wait_call(ccas_msg_blocking)

        # ----------------------------------------
        #   call completed and errors occured
        # ----------------------------------------
        test_tm.finished_calls[call_id] = ('driver', response_failure)

        with pytest.raises(Exception) as excinfo:
            test_tm.wait_call(ccas_msg_blocking)

        assert "something bad happened" == str(excinfo.value)

        # ----------------------------------------
        #   call not completed and blocking
        # ----------------------------------------
        test_tm.finished_calls = {}
        with pytest.raises(BlockedMessageException) as excinfo:
            test_tm.wait_call(ccas_msg_blocking)

        assert "message blocked because ***call 1 not finished" == str(excinfo.value)

        # ----------------------------------------
        #   call not completed and non-blocking
        # ----------------------------------------
        test_tm.finished_calls = {}
        with pytest.raises(IncompleteCallException) as excinfo:
            test_tm.wait_call(ccas_msg_nonblocking)

        assert "nonblocking wait_call() invoked before call 1 finished" == str(excinfo.value)
