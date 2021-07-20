# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
This file writes debug messages to 'debug.out' file if the environment
variable 'IPSES_DEBUG' is defined.
"""

import os


class Debug:  # pragma: no cover
    def __init__(self):
        self.file = None
        if 'IPSES_DEBUG' in os.environ:
            self.file = open('debug.out', 'w')

    def output(self, s, id1=0, id2=0):
        if self.file:
            tmp = ''
            if id1 != 0:
                """ one subscriber/listener """
                if id2 == 0:
                    tmp += ', id = ' + str(id1)
                else:
                    tmp += ', listenerid = ' + str(id1) + ', subscriberid = ' + str(id2)

            self.file.write(s + tmp + '\n')

    def msg(self, s1, ret=99, s2=''):
        if self.file:
            if s2 == '':
                if ret != 99:
                    self.file.write(s1 + ' ' + str(ret) + '\n')
                else:
                    self.file.write(s1 + '\n')
            else:
                if ret != 99:
                    self.file.write(s1 + ' ' + str(ret) + ' ' + s2 + '\n')
                else:
                    self.file.write(s1 + ' ' + s2 + '\n')

    def __del__(self):
        if self.file:
            self.file.close()


debug = Debug()
