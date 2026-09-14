# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
This file writes debug messages to 'debug.out' file if the environment
variable 'IPSES_DEBUG' is defined.
"""

import logging
import os

_logger = logging.getLogger(__name__)

if 'IPSES_DEBUG' in os.environ:
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(logging.FileHandler('debug.out', mode='w'))
else:
    _logger.setLevel(logging.WARNING)


def output(s: str, id1=0, id2=0):
    if id1 != 0:
        if id2 == 0:
            s += ', id = ' + str(id1)
        else:
            s += ', listenerid = ' + str(id1) + ', subscriberid = ' + str(id2)
    _logger.debug(s)
