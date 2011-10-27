import sys
import socket
import unittest
import logging, logging.handlers
sys.path.append('../..')
from resourceManager import *
from ipsExceptions import *

class faux_fwk(object):
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


class config_mgr(object):
    def __init__(self, host):
        self.host = host
    def get_platform_parameter(self, param):
        if param == 'HOST':
            return self.host
        else:
            raise Exception('bad param for testing')

class rmTestCase(unittest.TestCase):
    def setUp(self):
        # if you ar not working on jaguar or viz/mhd, this will give you 10 dummy nodes
        host = socket.gethostname()
        ff = faux_fwk(host)
        self.test_rm = ResourceManager(ff)
        self.test_rm.initialize(None, None, None, config_mgr(host))

    def test_add_nodes(self):
        # add nodes that don't already exist
        nodes_to_add = ['k','15','28', 17]
        new_ppn = 4
        self.test_rm.addNodes(nodes_to_add, new_ppn)
        for n in nodes_to_add:
            self.assert_(n in self.test_rm.availNodes,
                            'unable to add node' + str(n))
        # add existing nodes
        # ... not sure how to test that it does not add duplicates

    def test_change_node_status(self):
        tid = 639473
        self.test_rm.get_allocation('test_comp', 5, tid)
        my_allocated_node = self.test_rm.allocNodes[0]
        my_existing_node = self.test_rm.availNodes[0]
        my_nonexistent_node = 'my_nonexistent_node'  # should work, but not guaranteed, any other ideas???

        # set existing node to UP
        self.test_rm.setNodeState(my_existing_node, 'UP')
        self.assert_(self.test_rm.nodeTable[my_existing_node]['status'] == 'UP')

        # set existing node to DOWN
        self.test_rm.setNodeState(my_existing_node, 'DOWN')
        self.assert_(my_existing_node not in self.test_rm.nodeTable.keys())

        # set non-existing node to DOWN
        self.assertRaises(NonexistentResourceException, self.test_rm.setNodeState, my_nonexistent_node, 'DOWN')

        # set non-existing node to UP
        self.test_rm.setNodeState(my_nonexistent_node, 'UP')
        self.assert_(self.test_rm.nodeTable[my_nonexistent_node]['status'] == 'UP')

        # set allocated node to UP
        self.test_rm.setNodeState(my_allocated_node, 'UP')
        self.assert_(self.test_rm.nodeTable[my_allocated_node]['status'] == 'UP')

        # set allocated node to DOWN
        self.assertRaises(AllocatedNodeDownException, self.test_rm.setNodeState, my_allocated_node, 'DOWN')

    def test_allocate_node(self):
        # grab valid allocation
        tid1 = 639473
        self.assert_(self.test_rm.get_allocation('test_comp', 5, tid1))

        # grab valid allocation that does not work at the moment
        tid2 = 639474
        self.assertRaises(InsufficientResourcesException, self.test_rm.get_allocation, 'test_comp', 6, tid2)

        # release valid allocation
        self.assert_(self.test_rm.release_allocation(tid1))

        # grab invalid allocation
        self.assertRaises(BadResourceRequestException, self.test_rm.get_allocation, 'test_comp', 20, 3049753)


if __name__ == '__main__':
    unittest.main()
