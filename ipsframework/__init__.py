"""IPS Framework"""

from .component import Component
from .configuration_manager import ConfigurationManager
from .data_manager import DataManager
from .ips import Framework
from .resource_manager import ResourceManager
from .services import ServicesProxy, Task, TaskPool
from .task_manager import TaskManager

__all__ = [
    'Component',
    'ConfigurationManager',
    'DataManager',
    'Framework',
    'ResourceManager',
    'ServicesProxy',
    'Task',
    'TaskManager',
    'TaskPool',
]

from . import _version

__version__ = _version.get_versions()['version']
