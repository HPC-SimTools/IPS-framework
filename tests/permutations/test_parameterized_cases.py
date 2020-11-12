# -------------------------------------------------------------------------------
# Copyright 2006-2020 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import unittest


class ParameterizedTestCase(unittest.TestCase):
    """ TestCase classes that want to be parametrized should
        inherit from this class.
    """
    def __init__(self, methodName='runTest', param=None):
        # do_create_runspace=True, do_run_setup=True, do_run=True,
        # create_runspace_done=True, run_setup_done=True, run_done=True,
        # cfgFile_list=None, log_file=None, platform_filename=None):
        super(ParameterizedTestCase, self).__init__(methodName)
        self.param = param
#       self.do_create_runspace = do_create_runspace
#       self.do_run_setup = do_run_setup
#       self.do_run = do_run
#       self.create_runspace_done = create_runspace_done
#       self.run_setup_done = run_setup_done
#       self.run_done = run_done
#       self.cfgFile_list = cfgFile_list
#       self.log_file = log_file
#       self.platform_filename = platform_filename

    @staticmethod
    def parametrize(testcase_klass, param=None):
        """ Create a suite containing all tests taken from the given
            subclass, passing them the parameter 'param'.
        """
        testloader = unittest.TestLoader()
        testnames = testloader.getTestCaseNames(testcase_klass)
        suite = unittest.TestSuite()
        for name in testnames:
            suite.addTest(testcase_klass(name, param=param))
        return suite
