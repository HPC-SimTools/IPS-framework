# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Link to a description of the fault modeling piece of the rmpi project:
http://www.cs.sandia.gov/~rolf/app_model.html
"""

import os, sys
import random

# TODO: comment this code


def generate_event(fwk):
    """
    generates a list of times when failures will occur based on mtbf
    (in seconds) specified in the resource config file, one for each
    node since each node is treated independently of the others.
    the list is then sorted.

    does not account for the fact that the job was not started at the
    beginning of the hardware's lifespan.
    """
    nodes = self.RM.nodes
    return round(random.expovariate(float(nodes) / mtbf))


def trigger(fwk):
    to_kill = fwk.RM.failed_node()
    if to_kill:
        to_kill.state = 'failed'
    else:
        print('failure killed an unoccupied node')
    fwk.logEvent(None, None, 'node_failure', 'fault killed a node')
