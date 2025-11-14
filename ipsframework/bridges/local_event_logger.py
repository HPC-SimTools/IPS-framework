import datetime
import glob
import hashlib
import itertools
import json
import os
import re
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from ipsframework import ipsutil
from ipsframework.convert_log_function import convert_logdata_to_html
from ipsframework.services import ServicesProxy

if TYPE_CHECKING:
    from io import FileIO


def hash_file(file_name):  # pragma: no cover
    """
    Return the MD5 hash of a file
    :rtype: str
    :param file_name: Full path to file
    :return: MD5 of file_name
    """
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(file_name, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()


class SimulationData:
    """
    Container for simulation data.
    """

    def __init__(self):
        self.counter = 0
        self.monitor_file_name = ''
        self.portal_runid = ''
        self.parent_portal_runid = ''
        self.sim_name = ''
        self.sim_root = ''
        self.monitor_file: FileIO = None  # type: ignore
        self.json_monitor_file: FileIO = None  # type: ignore
        self.phys_time_stamp = -1
        self.monitor_url = ''
        self.bigbuf = ''


class LocalEventLogger:
    """The LocalEventLogger class manages event logging for the supplemental bridge components."""

    def __init__(self) -> None:
        # self.curTime = time.localtime()
        # self.startTime = self.curTime
        self.counter = 0
        self.dump_freq = 10
        self.min_dump_interval = 300  # Minimum time interval in Sec for HTML dump operation
        self.last_dump_time = time.time()
        self.write_to_htmldir = True
        self.html_dir = ''
        self.first_portal_runid = None

    def init(self, services: ServicesProxy) -> None:
        """Called from the bridge component's `init` function."""
        try:
            freq = int(services.get_config_param('HTML_DUMP_FREQ', silent=True))
        except Exception:
            pass
        else:
            self.dump_freq = freq

        try:
            self.html_dir = services.get_config_param('USER_W3_DIR', silent=True) or ''
        except Exception:
            services.warning('Missing USER_W3_DIR configuration - disabling web-visible logging')
            self.write_to_htmldir = False
        else:
            if self.html_dir.strip() == '':
                services.warning('Empty USER_W3_DIR configuration - disabling web-visible logging')
                self.write_to_htmldir = False
            else:
                try:
                    os.mkdir(self.html_dir)
                except FileExistsError:
                    pass
                except Exception:
                    services.warning('Unable to create HTML directory - disabling web-visible logging')
                    self.write_to_htmldir = False

    def finalize(self, sim_map: dict[str, SimulationData]) -> None:
        for sim_data in sim_map.values():
            try:
                sim_data.monitor_file.close()
                sim_data.json_monitor_file.close()
            except Exception:
                pass

    def init_simulation(self, services: ServicesProxy, sim_name: str, sim_root: str, hostname: str, username: str) -> SimulationData:
        """
        Create and send information about simulation *sim_name* living in
        *sim_root* so the portal can set up corresponding structures to manage
        data from the sim.

        :returns:
        """
        sim_data = SimulationData()
        sim_data.sim_name = sim_name
        sim_data.sim_root = sim_root

        d = datetime.datetime.now()
        date_str = '%s.%03d' % (d.strftime('%Y-%m-%dT%H:%M:%S'), int(d.microsecond / 1000))
        sim_data.portal_runid = f'{sim_name}_{hostname}_{username}_{date_str}'
        try:
            services.set_config_param('PORTAL_RUNID', sim_data.portal_runid, target_sim_name=sim_name)
        except Exception:
            services.error('Simulation %s is not accessible', sim_name)
            return

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
            services.exception('Error creating Simulation Log directory %s : %d %s' % (sim_log_dir, oserr.errno, oserr.strerror))
            raise

        sim_data.monitor_file_name = os.path.join(sim_log_dir, sim_data.portal_runid + '.eventlog')
        try:
            sim_data.monitor_file = open(sim_data.monitor_file_name, 'wb', 0)
        except IOError as oserr:
            services.error('Error opening file %s: error(%s): %s' % (sim_data.monitor_file_name, oserr.errno, oserr.strerror))
            services.error('Using /dev/null instead')
            sim_data.monitor_file = open('/dev/null', 'w')
        json_fname = sim_data.monitor_file_name.replace('eventlog', 'jsonl')
        sim_data.json_monitor_file = open(json_fname, 'w')

        return sim_data

    def send_event(self, services: ServicesProxy, sim_data: SimulationData, event_data: dict[str, Any]):
        """
        Send contents of *event_data* and *sim_data* to portal.
        """
        timestamp = ipsutil.getTimeString()
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
        if ((self.counter % freq == 0) and (time.time() - self.last_dump_time > self.min_dump_interval)) or (event_data['eventtype'] == 'IPS_END'):
            self.last_dump_time = time.time()
            html_filename = sim_data.monitor_file_name.replace('eventlog', 'html')
            html_page = convert_logdata_to_html(sim_data.bigbuf)
            open(html_filename, 'w').writelines(html_page)
            if self.write_to_htmldir:
                html_file = os.path.join(self.html_dir, os.path.basename(html_filename))
                try:
                    open(html_file, 'w').writelines(html_page)
                except Exception:
                    services.exception('Error writing html file into USER_W3_DIR directory')
                    self.write_to_htmldir = False
