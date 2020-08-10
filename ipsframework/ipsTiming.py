# -------------------------------------------------------------------------------
# Copyright 2006-2012 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
"""
Experimental timing of the IPS using TAU
"""

import os
import sys
import inspect
if (sys.version_info > (2, 6)):
    from types import MethodType
else:
    from new import instancemethod as MethodType


IPS_TIMING = False
try:
    if os.environ['IPS_TIMING'] == '1':
        try:
            import pytau
        except:
            raise
        IPS_TIMING = True
except KeyError:
    pass


def create_timer(name, fnc, pid):
    try:
        if os.environ['IPS_TIMING'] == '1':
            # import pytau
            # print 'created a timer', name + '.' + fnc, ' - ', pid
            return pytau.profileTimer(name + '.' + fnc, '', str(pid))
        # else:
            # print 'timing not on'
    except Exception as e:
        # print "*********** NO TIMING *************"
        # print e
        return None


def start(timer):
    if timer != None:
        # import pytau
        pytau.start(timer)
    else:
        pass


def stop(timer):
    if timer != None:
        # import pytau
        pytau.stop(timer)
    else:
        pass


def dumpAll(label=""):
    try:
        if os.environ['IPS_TIMING'] == '1':
            # import pytau
            if label != "":
                pytau.dbDump()
            else:
                pytau.dbDump(label)
        # else:
        #    print 'timing not on'
    except KeyError:
        pass
    except Exception as e:
        print('something happened during dump')
        raise


class TauWrap:
    def __init__(self, timer):
        self.timer = timer

    def __call__(self, func):
        def wrapper(*arg, **keywords):
            start(self.timer)
            try:
                res = func(*arg, **keywords)
            except:
                stop(self.timer)
#                dumpAll()
                raise
            else:
                stop(self.timer)
#                dumpAll()
                return res
        return wrapper


def weave_tau_timer(self, target):

    def wrapper(self, *args, **kwargs):
        timers_dict_name = '_tau_timers_' + str(id(self))
        try:
            timer = getattr(self, timers_dict_name)[target.__name__]
        except KeyError:
            print('weave_tau_timer: Key error : ', target.__name__)
            return target(self, *args, **kwargs)
#        print 'Starting timer for ', target.__name__, timer
        start(timer)
        try:
            ret_val = target(self, *args, **kwargs)
        except:
            stop(timer)
            raise
        stop(timer)
#        print 'Stopped timer for ', target.__name__, timer
        return ret_val
    return wrapper


def instrument_object_with_tau(obj_name, obj, exclude=None):
    if not IPS_TIMING:
        return
    if not exclude:
        my_exclude = []
    else:
        my_exclude = exclude

    timers_dict_name = '_tau_timers_' + str(id(obj))
    try:
        timers_dict = getattr(obj, timers_dict_name)
    except AttributeError:
        timers_dict = {}
    raw_method_dict_name = '_raw_method_' + str(id(obj))
    try:
        raw_method_dict = getattr(obj, raw_method_dict_name)
    except AttributeError:
        raw_method_dict = {}
        for name, value in obj.__class__.__dict__.items():
            if (inspect.ismethod(getattr(obj, name))):
                raw_method_dict[name] = value
    pid = os.getpid()
    for name, value in obj.__class__.__dict__.items():
        if (name not in my_exclude):
            if (callable(value)):
                timers_dict[name] = create_timer(obj_name, name, pid)

    for name, method in raw_method_dict.items():
        if (name not in my_exclude):
            wrapped_method = weave_tau_timer(obj, method)
            method_obj = MethodType(wrapped_method, obj, obj.__class__)
            setattr(obj, name, method_obj)

    setattr(obj, timers_dict_name, timers_dict)
    setattr(obj, raw_method_dict_name, raw_method_dict)
    return


"""
t1 = create_timer('test', 'a', str(os.getpid()))
start(t1)
time.sleep(3)
stop(t1)
dumpAll('blargh')
"""
