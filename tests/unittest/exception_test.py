#-------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
#-------------------------------------------------------------------------------
import sys
sys.path.append('..')
from frameworkpath import *
sys.path.append(fsrc)
from ipsExceptions import BadResourceRequestException, InsufficientResourcesException

def check_BRRE():
    raise BadResourceRequestException(1234, 413, 13, 5)

def check_IRE():
    raise InsufficientResourcesException(3333, 1928717364, 2374927, 5)

if __name__=="__main__":
    try:
        check_BRRE()
    #except BadResourceRequestException, e:
    except Exception as e:
        print('BRRE with comma e, print e')
        print(e)
        print(e.__str__())

    print('------------')
    try:
        check_IRE()
    except Exception as e:
        print('IRE with comma e, print e')
        print(e)
