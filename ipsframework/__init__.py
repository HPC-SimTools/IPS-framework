"""IPS Framework"""
from .component import Component
from .configurationManager import ConfigurationManager
from .dataManager import DataManager
from .ips import Framework
from .resourceManager import ResourceManager
from .services import ServicesProxy, TaskPool, Task
from .taskManager import TaskManager

__all__ = ['Component',
           'ConfigurationManager',
           'DataManager',
           'Framework',
           'ResourceManager',
           'ServicesProxy',
           'TaskPool',
           'Task',
           'TaskManager']

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
