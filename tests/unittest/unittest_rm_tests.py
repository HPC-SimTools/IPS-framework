# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import pytest
import socket
import logging
import logging.handlers
from ipsframework.resourceManager import ResourceManager
from ipsframework.ipsExceptions import (NonexistentResourceException,
                                        AllocatedNodeDownException,
                                        InsufficientResourcesException,
                                        BadResourceRequestException)


class faux_fwk:
    def __init__(self, host):
        self.host = host
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
        except:
            print('error in Framework.debug', args)
            raise

    def warning(self, *args):
        try:
            self.current_logger.warning(*args)
        except:
            print('error in Framework.warning', args)
            raise


class config_mgr:
    class faux_comp:
        sim_root = "test_sim_root"
    sim_map = {"test_sim": faux_comp()}
    fwk_sim_name = "test_sim"

    def __init__(self, host):
        self.host = host

    def get_platform_parameter(self, param, silent=False):
        if param == 'HOST':
            return self.host
        elif param == 'NODE_ALLOCATION_MODE':
            return "shared"
        elif param == 'NODES':
            return 5
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
                raise Exception('bad param for testing')
            else:
                return None


class TestRmCase:

    def test_add_nodes(self):
        host = socket.gethostname()
        self.test_rm = ResourceManager(faux_fwk(host))
        self.test_rm.initialize(None, None, config_mgr(host), None)
        # add nodes that don't already exist
        new_ppn = 4
        nodes_to_add = [('k', new_ppn), ('15', new_ppn), ('28', new_ppn), (17, new_ppn)]
        self.test_rm.add_nodes(nodes_to_add)
        for n, p in nodes_to_add:
            assert n in self.test_rm.avail_nodes
        # add existing nodes
        # ... not sure how to test that it does not add duplicates

    def xtest_change_node_status(self):
        tid = 639473
        self.test_rm.get_allocation('test_comp', 5, tid, False, False)
        my_allocated_node = self.test_rm.alloc_nodes[0]
        my_existing_node = self.test_rm.avail_nodes[0]
        my_nonexistent_node = 'my_nonexistent_node'  # should work, but not guaranteed, any other ideas???

        # set existing node to UP
        self.test_rm.setNodeState(my_existing_node, 'UP')
        self.assertTrue(self.test_rm.nodeTable[my_existing_node]['status'] == 'UP')

        # set existing node to DOWN
        self.test_rm.setNodeState(my_existing_node, 'DOWN')
        self.assertTrue(my_existing_node not in list(self.test_rm.nodeTable.keys()))

        # set non-existing node to DOWN
        self.assertRaises(NonexistentResourceException, self.test_rm.setNodeState, my_nonexistent_node, 'DOWN')

        # set non-existing node to UP
        self.test_rm.setNodeState(my_nonexistent_node, 'UP')
        self.assertTrue(self.test_rm.nodeTable[my_nonexistent_node]['status'] == 'UP')

        # set allocated node to UP
        self.test_rm.setNodeState(my_allocated_node, 'UP')
        self.assertTrue(self.test_rm.nodeTable[my_allocated_node]['status'] == 'UP')

        # set allocated node to DOWN
        self.assertRaises(AllocatedNodeDownException, self.test_rm.setNodeState, my_allocated_node, 'DOWN')

    def test_allocate_node(self):
        host = socket.gethostname()
        self.test_rm = ResourceManager(faux_fwk(host))
        self.test_rm.initialize(None, None, config_mgr(host), None)
        # grab valid allocation
        tid1 = 639473
        assert self.test_rm.get_allocation('test_comp', 5, tid1, False, False)

        # grab valid allocation that does not work at the moment
        tid2 = 639474
        with pytest.raises(InsufficientResourcesException) as excinfo:
            self.test_rm.get_allocation('test_comp', 6, tid2, False, False)

        assert "component test_comp requested 3 nodes, which is more than available by -2 nodes, for task 639474." == str(excinfo.value)

        # release valid allocation
        assert self.test_rm.release_allocation(tid1, None)

        # grab invalid allocation
        with pytest.raises(BadResourceRequestException) as excinfo:
            self.test_rm.get_allocation('test_comp', 20, 3049753, False, False)

        assert "component test_comp requested 10 nodes, which is more than possible by 5 nodes, for task 3049753." == str(excinfo.value)
