#!/usr/bin/env python3
""" Component wrapper for the ensemble example for `a_sim`. """
from ipsframework import Component
# from ipsframework.resourceHelper import getResourceList
from doc.examples.ensembles.environment import get_platform_info

class a_sim_comp(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
        print('Created %s' % (self.__class__))

    def step(self, timestamp=0.0):
        # TODO echo parameters for this run
        print('Hello from a_sim_comp')

        # Echo the parameters we're expecting, A, B, and C
        print(f'a_sim_comp parameters: A={self.A}, B={self.B}, C={self.C}')

        # Now show the h/w config
        # print(f'services={self.services} and type {type(self.services)}')
        # This function is a lie in that the interface says it wants services
        # when it really needs a configuration manager reference, and one
        # cannot get that from a Component object.
        # list_of_nodes, cpn, spn, ppn, accurate_nodes = getResourceList(self.services,
        #                                                                host="")
        # print(f'list_of_nodes={list_of_nodes}')
        # print(f'cpn={cpn}')
        # print(f'spn={spn}')
        # print(f'ppn={ppn}')
        # print(f'accurate_nodes={accurate_nodes}')

        run_env = get_platform_info()
        self.services.info(run_env)

