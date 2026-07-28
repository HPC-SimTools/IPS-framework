""" Provides information about the runtime environment

"""
import psutil
import platform
import os


def get_platform_info():
    """ Get information about the platform

    :returns: A dictionary containing hostname, cpu count, cpu core id for
        current running process, and available GPU devices if set
    """
    result = {'hostname': platform.node(),
              'cpu_count': psutil.cpu_count(),
              'pid': os.getpid()}

    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        result['cuda_visible_devices'] = os.environ['CUDA_VISIBLE_DEVICES']

    try:
        p = psutil.Process()
        with p.oneshot():
            result['core_id'] = p.cpu_num()
    except:
        # cpu_num() only available on linux (and BSD systems), so this will
        # throw an exception on other platforms
        pass

    return result
