import sys
sys.path.append('../..')
from ipsExceptions import BadResourceRequestException, InsufficientResourcesException

def check_BRRE():
    raise BadResourceRequestException(1234, 413, 13, 5)

def check_IRE():
    raise InsufficientResourcesException(3333, 1928717364, 2374927, 5)

if __name__=="__main__":
    try:
        check_BRRE()
    #except BadResourceRequestException, e:
    except Exception, e:
        print 'BRRE with comma e, print e'
        print e
        print e.__str__()

    print '------------'
    try:
        check_IRE()
    except Exception, e:
        print 'IRE with comma e, print e'
        print e
