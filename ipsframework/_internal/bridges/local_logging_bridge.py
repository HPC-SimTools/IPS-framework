# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import hashlib
import json
import os
import time
from typing import TYPE_CHECKING, Any, Literal

from ipsframework import Component, ipsutil
from ipsframework.cca_es_spec import Event
from ipsframework.convert_log_function import convert_logdata_to_html

if TYPE_CHECKING:
    from io import FileIO


class SimulationData:
    """
    Container for simulation data.
    """

    def __init__(self):
        self.counter = 0
        self.monitor_file_prefix = ''
        """The name of the file, minus the extension ('.html', '.jsonl', etc.).

        If this is empty, you must either check to see if you can create the file, or you should assume that you can't create the file.
        """
        self.portal_runid: str | None = None
        """Portal RunID, set by component which publishes the IPS_START event. Only used for logging here."""
        self.parent_portal_runid: str | None = None
        """Parent portal RunID, derived from locally determined portal RunID. Should explicitly be None (not empty string) if not set. Only used for logging."""
        self.sim_name = ''
        self.sim_root = ''
        self.monitor_file: FileIO = None  # type: ignore
        self.json_monitor_file: FileIO = None  # type: ignore
        self.bigbuf = ''
        self.phys_time_stamp = -1
        self.monitor_url = ''


class LocalLoggingBridge(Component):
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
        self.counter = 0
        self.dump_freq = 10
        self.min_dump_interval = 300  # Minimum time interval in Sec for HTML dump operation
        self.last_dump_time = time.time()
        self.write_to_htmldir = True
        self.html_dir = ''
        self.first_portal_runid = None

    def init(self, timestamp=0.0, **keywords):
        """
        Subscribe to *_IPS_MONITOR* events and register callback :py:meth:`.process_event`.
        """
        self.services.subscribe('_IPS_MONITOR', 'process_event')

        try:
            freq = int(self.services.get_config_param('HTML_DUMP_FREQ', silent=True))
        except Exception:
            pass
        else:
            self.dump_freq = freq

        try:
            self.html_dir = self.services.get_config_param('USER_W3_DIR', silent=True) or ''
        except Exception:
            self.services.warning(
                'Missing USER_W3_DIR configuration - disabling web-visible logging'
            )
            self.write_to_htmldir = False
        else:
            if self.html_dir.strip() == '':
                self.services.warning(
                    'Empty USER_W3_DIR configuration - disabling web-visible logging'
                )
                self.write_to_htmldir = False
            else:
                try:
                    os.mkdir(self.html_dir)
                except FileExistsError:
                    pass
                except Exception:
                    self.services.warning(
                        'Unable to create HTML directory - disabling web-visible logging'
                    )
                    self.write_to_htmldir = False

    def step(self, timestamp=0.0, **keywords):
        """
        Poll for events.
        """
        while not self.done:
            self.services.process_events()
            time.sleep(0.5)

    def finalize(self, timestamp=0.0, **keywords):
        for sim_data in self.sim_map.values():
            try:
                sim_data.monitor_file.close()
                sim_data.json_monitor_file.close()
            except Exception:
                pass

    def process_event(self, topic_name: str, the_event: Event):
        """
        Process a single event *the_event* on topic *topic_name*.
        """
        event_body = the_event.get_body()
        sim_name = event_body['sim_name']
        portal_data = event_body['portal_data']
        try:
            portal_data['sim_name'] = event_body['real_sim_name']
        except KeyError:
            portal_data['sim_name'] = sim_name

        if portal_data['eventtype'] == 'IPS_START':
            sim_root = event_body['sim_root']
            self.init_simulation(sim_name, sim_root, portal_data['portal_runid'])

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
            portal_data['trace']['traceId'] = hashlib.md5(
                sim_data.portal_runid.encode()
            ).hexdigest()

        self.send_event(sim_data, portal_data)

        if portal_data['eventtype'] == 'IPS_END':
            del self.sim_map[sim_name]

        if len(self.sim_map) == 0:
            self.done = True
            self.services.debug('No more simulation to monitor - exiting')
            time.sleep(1)

    def init_simulation(self, sim_name: str, sim_root: str, portal_runid: str):
        """
        Create and send information about simulation *sim_name* living in
        *sim_root* so the portal can set up corresponding structures to manage
        data from the sim.
        """
        self.services.debug(
            'Initializing simulation using BasicBridge: %s -- %s ', sim_name, sim_root
        )

        sim_data = SimulationData()
        sim_data.sim_name = sim_name
        sim_data.sim_root = sim_root

        sim_data.portal_runid = portal_runid

        if self.first_portal_runid:
            sim_data.parent_portal_runid = self.first_portal_runid
        else:
            self.first_portal_runid = sim_data.portal_runid

        if sim_data.sim_root.strip() == '.':
            sim_data.sim_root = os.environ['IPS_INITIAL_CWD']
        sim_log_dir = os.path.join(sim_data.sim_root, 'simulation_log')
        try:
            os.makedirs(sim_log_dir, exist_ok=True)
        except OSError as oserr:
            self.services.exception(
                'Error creating Simulation Log directory %s : %d %s'
                % (sim_log_dir, oserr.errno, oserr.strerror)
            )
            raise

        sim_data.monitor_file_prefix = os.path.join(sim_log_dir, sim_data.portal_runid)
        eventlog_fname = f'{sim_data.monitor_file_prefix}.eventlog'
        try:
            sim_data.monitor_file = open(eventlog_fname, 'wb', 0)
        except OSError as oserr:
            self.services.error(
                'Error opening file %s: error(%s): %s'
                % (eventlog_fname, oserr.errno, oserr.strerror)
            )
            self.services.error('Using /dev/null instead')
            sim_data.monitor_file_prefix = ''
            sim_data.monitor_file = open('/dev/null', 'w')

        if sim_data.monitor_file_prefix:
            json_fname = os.path.join(sim_log_dir, sim_data.portal_runid + '.jsonl')
            sim_data.json_monitor_file = open(json_fname, 'w')
        else:
            sim_data.json_monitor_file = open('/dev/null', 'w')

        self.sim_map[sim_data.sim_name] = sim_data

    def terminate(self, status: Literal[0, 1]):
        """
        Clean up services and call :py:obj:`sys_exit`.
        """

        Component.terminate(self, status)

    def send_event(self, sim_data: SimulationData, event_data: dict[str, Any]):
        """
        Send contents of *event_data* and *sim_data* to portal.
        """
        timestamp = ipsutil.get_time_string()
        buf = '%8d %s ' % (sim_data.counter, timestamp)
        for k, v in event_data.items():
            if len(str(v).strip()) == 0:
                continue
            if ' ' in str(v):
                buf += "%s='%s' " % (k, str(v))
            else:
                buf += '%s=%s ' % (k, str(v))
        buf += '\n'
        sim_data.monitor_file.write(bytes(buf, encoding='UTF-8'))
        sim_data.bigbuf += buf

        buf = json.dumps(event_data)
        sim_data.json_monitor_file.write('%s\n' % buf)

        freq = self.dump_freq
        if (
            (self.counter % freq == 0)
            and (time.time() - self.last_dump_time > self.min_dump_interval)
        ) or (event_data['eventtype'] == 'IPS_END'):
            self.last_dump_time = time.time()
            if sim_data.monitor_file_prefix:
                html_filename = f'{sim_data.monitor_file_prefix}.html'
                html_page = convert_logdata_to_html(sim_data.bigbuf)
                open(html_filename, 'w').writelines(html_page)
                if self.write_to_htmldir:
                    html_file = os.path.join(self.html_dir, os.path.basename(html_filename))
                    try:
                        open(html_file, 'w').writelines(html_page)
                    except Exception:
                        self.services.exception(
                            'Error writing html file into USER_W3_DIR directory'
                        )
                        self.write_to_htmldir = False
