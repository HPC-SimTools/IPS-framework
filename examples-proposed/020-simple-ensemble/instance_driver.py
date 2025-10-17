#!/usr/bin/env python3
"""
    Driver component for instances
"""
from ipsframework import Component


class InstanceDriver(Component):
    """
        Instance driver component that steps the main component
    """

    def step(self, timestamp: float = 0.0, **keywords):
        instance_component = self.services.get_port('COMPONENT')

        self.services.call(instance_component, 'step', 0.0)

