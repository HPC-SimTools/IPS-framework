"""IPS Framework"""

from .component import Component
from .configurationManager import ConfigurationManager
from .dataManager import DataManager
from .ips import Framework
from .resourceManager import ResourceManager
from .services import ServicesProxy, Task, TaskPool
from .taskManager import TaskManager

__all__ = ['Component', 'ConfigurationManager', 'DataManager', 'Framework', 'ResourceManager', 'ServicesProxy', 'Task', 'TaskManager', 'TaskPool']

from . import _version
__version__ = _version.get_versions()['version']
