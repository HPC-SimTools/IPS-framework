# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import hashlib
import time
from typing import Literal

from ipsframework import Component
from ipsframework.bridges.local_event_logger import LocalEventLogger, SimulationData
from ipsframework.cca_es_spec import Event


class BasicBridge(Component):
    """
    Framework component meant to handle simple event logging.

    This component should not exist in the event that the simulation is interacting with the web framework - see the PortalBridge component instead.
    """

    def __init__(self, services, config):
        """
        Declaration of private variables and initialization of
        :py:class:`component.Component` object.
        """
        super().__init__(services, config)
        self.sim_map: dict[str, SimulationData] = {}
        self.done = False
        self.local_event_logger = LocalEventLogger()

    def init(self, timestamp=0.0, **keywords):
        """
        Subscribe to *_IPS_MONITOR* events and register callback :py:meth:`.process_event`.
        """
        self.services.subscribe('_IPS_MONITOR', 'process_event')
        self.local_event_logger.init(self.services)

    def step(self, timestamp=0.0, **keywords):
        """
        Poll for events.
        """
        while not self.done:
            self.services.process_events()
            time.sleep(0.5)

    def finalize(self, timestamp=0.0, **keywords):
        self.local_event_logger.finalize(self.sim_map)

    def process_event(self, topicName: str, theEvent: Event):
        """
        Process a single event *theEvent* on topic *topicName*.
        """
        event_body = theEvent.getBody()
        sim_name = event_body['sim_name']
        portal_data = event_body['portal_data']
        try:
            portal_data['sim_name'] = event_body['real_sim_name']
        except KeyError:
            portal_data['sim_name'] = sim_name

        if portal_data['eventtype'] == 'IPS_START':
            sim_root = event_body['sim_root']
            self.init_simulation(sim_name, sim_root)

        sim_data = self.sim_map[sim_name]
        if portal_data['eventtype'] == 'PORTALBRIDGE_UPDATE_TIMESTAMP':
            sim_data.phys_time_stamp = portal_data['phystimestamp']
            return
        else:
            portal_data['phystimestamp'] = sim_data.phys_time_stamp

        if portal_data['eventtype'] == 'PORTAL_REGISTER_NOTEBOOK':
            return

        if portal_data['eventtype'] == 'PORTAL_ADD_JUPYTER_DATA':
            return

        if portal_data['eventtype'] == 'PORTAL_UPLOAD_ENSEMBLE_PARAMS':
            return

        portal_data['portal_runid'] = sim_data.portal_runid

        if portal_data['eventtype'] == 'IPS_SET_MONITOR_URL':
            sim_data.monitor_url = portal_data['vizurl']
        elif sim_data.monitor_url:
            portal_data['vizurl'] = sim_data.monitor_url

        if portal_data['eventtype'] == 'IPS_START' and 'parent_portal_runid' not in portal_data:
            portal_data['parent_portal_runid'] = sim_data.parent_portal_runid
        portal_data['seqnum'] = sim_data.counter

        if 'trace' in portal_data:
            portal_data['trace']['traceId'] = hashlib.md5(sim_data.portal_runid.encode()).hexdigest()

        self.local_event_logger.send_event(self.services, sim_data, portal_data)

        if portal_data['eventtype'] == 'IPS_END':
            del self.sim_map[sim_name]

        if len(self.sim_map) == 0:
            self.done = True
            self.services.debug('No more simulation to monitor - exiting')
            time.sleep(1)

    def init_simulation(self, sim_name: str, sim_root: str):
        """
        Create and send information about simulation *sim_name* living in
        *sim_root* so the portal can set up corresponding structures to manage
        data from the sim.
        """
        self.services.debug('Initializing simulation using BasicBridge: %s -- %s ', sim_name, sim_root)
        sim_data = self.local_event_logger.init_simulation(self.services, sim_name, sim_root, self.HOST, self.USER)
        self.sim_map[sim_data.sim_name] = sim_data

    def terminate(self, status: Literal[0, 1]):
        """
        Clean up services and call :py:obj:`sys_exit`.
        """

        Component.terminate(self, status)
