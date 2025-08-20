# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Resource Usage Simulator (RUS)
------------------------------

by Samantha Foley, Indiana University
3/4/2010

This RUS simulates the resource usage of a MCMD application as described
by the input files.  It is a tool that helps to determine what resource
allocation algorithms and component configurations work best for classes
of applications.
"""

import sys, os
from configobj import ConfigObj


class phase:
    """
    manages the different characteristics of different phases of execution that may occur over the course of a single IPS run for a given simulation..
    """

    def __init__(self, info_dict, fwk, sim, name, old_style=False):
        """
        keep track of things for each phase
        """
        self.name = name
        self.fwk = fwk
        self.nsteps = 0
        self.comp_list = []
        if old_style:
            return

        try:
            self.nsteps = int(info_dict['nsteps'])
        except:
            print('bad nsteps in phase %s' % self.name)
            raise
        try:
            self.comp_list = info_dict['components']
        except:
            print('bad components in phase %s' % self.name)
            raise
