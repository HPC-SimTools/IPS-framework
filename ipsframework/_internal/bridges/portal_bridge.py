# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import hashlib
import json
import logging
import logging.config
import os
import tarfile
import time
from collections.abc import Callable
from multiprocessing import Event, Pipe, Process
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event as EventType
from pathlib import Path
from typing import Any, Literal

from urllib3 import PoolManager
from urllib3.exceptions import MaxRetryError
from urllib3.util import Retry as Urllib3Retry

from ipsframework import Component

MAX_RETRIES = 10


_portal_logger = logging.getLogger('ipsframework.bridges.portal_bridge')

EVENT_MESSAGE_TYPE = 'events'
DATA_MESSAGE_TYPE = 'data'
NOTEBOOK_MESSAGE_TYPE = 'notebook'
ENSEMBLE_MESSAGE_TYPE = 'ensemble'


def send_post(conn: Connection, stop: EventType, url: str):
    fail_count = 0

    http = PoolManager(
        retries=Urllib3Retry(total=MAX_RETRIES, backoff_factor=1, respect_retry_after_header=True),
        headers={'Content-Type': 'application/json'},
    )

    # TODO - try to figure out ways to send the sim_names back for events, not essential though
    while True:
        if conn.poll(0.1):
            msgs = []
            while conn.poll(0.01):
                msgs.append(conn.recv())
            try:
                start_walltime = time.time()
                resp = http.request('POST', url, body=json.dumps(msgs).encode())
                _portal_logger.debug('HTTP event took %s seconds', time.time() - start_walltime)
            except MaxRetryError as e:
                fail_count += 1
                conn.send((EVENT_MESSAGE_TYPE, '', 999, f'Max retry error: {e}'))
            else:
                conn.send((EVENT_MESSAGE_TYPE, '', resp.status, resp.data.decode()))
                fail_count = 0

            if fail_count >= MAX_RETRIES:
                conn.send((EVENT_MESSAGE_TYPE, '', -1, 'Too many consecutive failed connections'))
                break
        elif stop.is_set():
            break


def send_jupyter_notebook(conn: Connection, stop: EventType, url: str, api_key: str, username: str):
    fail_count = 0

    http = PoolManager(
        retries=Urllib3Retry(total=MAX_RETRIES, backoff_factor=1, respect_retry_after_header=True)
    )

    while True:
        if conn.poll(0.1):
            next_val: dict[str, Any] = conn.recv()
            # TODO - consider using multipart/form-data instead
            try:
                start_walltime = time.time()
                resp = http.request(
                    'POST',
                    url,
                    body=next_val['data'],
                    headers={
                        'X-Api-Key': api_key,
                        'Content-Type': 'application/octet-stream',
                        'X-Ips-Username': username,
                        'X-Ips-Portal-Runid': next_val['portal_runid'],
                        'X-Ips-Filename': next_val['filename'],
                    },
                )
                _portal_logger.debug(
                    'Notebook HTTP request took %s seconds',
                    time.time() - start_walltime,
                )
            except MaxRetryError as e:
                fail_count += 1
                conn.send(
                    (NOTEBOOK_MESSAGE_TYPE, next_val['component_id'], 999, f'Max retry error: {e}')
                )
            else:
                conn.send(
                    (
                        NOTEBOOK_MESSAGE_TYPE,
                        next_val['component_id'],
                        resp.status,
                        resp.data.decode(),
                    )
                )
                fail_count = 0

            if fail_count >= MAX_RETRIES:
                conn.send(
                    (
                        NOTEBOOK_MESSAGE_TYPE,
                        next_val['component_id'],
                        -1,
                        'Too many consecutive failed connections',
                    )
                )
                break
        elif stop.is_set():
            break


def send_jupyter_notebook_data(
    conn: Connection, stop: EventType, url: str, api_key: str, username: str
):
    fail_count = 0

    http = PoolManager(
        retries=Urllib3Retry(total=MAX_RETRIES, backoff_factor=1, respect_retry_after_header=True)
    )

    while True:
        if conn.poll(0.1):
            next_val: dict[str, Any] = conn.recv()
            # TODO - consider using multipart/form-data instead
            try:
                headers = {
                    'X-Api-Key': api_key,
                    'Content-Type': 'application/octet-stream',
                    'X-Ips-Username': username,
                    'X-Ips-Portal-Runid': next_val['portal_runid'],
                    'X-Ips-Filename': next_val['filename'],
                    'X-Ips-Tag': str(next_val['tag']),
                }
                if next_val.get('replace'):
                    headers['X-Ips-Replace'] = 'true'
                data_archive_format = next_val.get('data_archive_format')
                if data_archive_format:
                    headers['X-Ips-Archive-Format'] = data_archive_format
                # TODO - we should send the body in CHUNKS here.
                with open(next_val['data_source'], 'rb') as f:
                    body = f.read()
                start_walltime = time.time()
                resp = http.request(
                    'POST',
                    url,
                    body=body,
                    headers=headers,
                )
                _portal_logger.debug(
                    'Notebook HTTP request took %s seconds',
                    time.time() - start_walltime,
                )
            except (MaxRetryError, OSError) as e:
                fail_count += 1
                conn.send(
                    (DATA_MESSAGE_TYPE, next_val['component_id'], 999, f'Max retry error: {e}')
                )
            else:
                conn.send(
                    (DATA_MESSAGE_TYPE, next_val['component_id'], resp.status, resp.data.decode())
                )
                fail_count = 0

            if fail_count >= MAX_RETRIES:
                conn.send(
                    (
                        DATA_MESSAGE_TYPE,
                        next_val['component_id'],
                        -1,
                        'Too many consecutive failed connections',
                    )
                )
                break
        elif stop.is_set():
            break


def send_ensemble_variables(
    conn: Connection, stop: EventType, url: str, api_key: str, username: str
):
    fail_count = 0

    http = PoolManager(
        retries=Urllib3Retry(total=MAX_RETRIES, backoff_factor=1, respect_retry_after_header=True)
    )

    while True:
        if conn.poll(0.1):
            next_val: dict[str, Any] = conn.recv()
            try:
                headers = {
                    'X-Api-Key': api_key,
                    'Content-Type': 'text/csv',
                    'X-Ips-Username': username,
                    'X-Ips-Portal-Runid': next_val['portal_runid'],
                    'X-Ips-Component-Name': next_val['component_name'],
                    'X-Ips-Ensemble-Name': next_val['ensemble_name'],
                    'X-Ips-Ensemble-Id': next_val['ensemble_id'],
                }
                # TODO check to see that file size is < 1MB
                with open(next_val['ensemble_data_path'], 'rb') as fd:
                    body = fd.read()
                start_walltime = time.time()
                resp = http.request(
                    'POST',
                    url,
                    body=body,
                    headers=headers,
                )
                _portal_logger.debug(
                    'Ensemble CSV response took %s seconds',
                    time.time() - start_walltime,
                )
            except (MaxRetryError, OSError) as e:
                fail_count += 1
                conn.send(
                    (ENSEMBLE_MESSAGE_TYPE, next_val['component_id'], 999, f'Max retry error: {e}')
                )
            else:
                conn.send(
                    (
                        ENSEMBLE_MESSAGE_TYPE,
                        next_val['component_id'],
                        resp.status,
                        resp.data.decode(),
                    )
                )
                fail_count = 0

            if fail_count >= MAX_RETRIES:
                conn.send(
                    (
                        ENSEMBLE_MESSAGE_TYPE,
                        next_val['component_id'],
                        -1,
                        'Too many consecutive failed connections',
                    )
                )
                break
        elif stop.is_set():
            break


class UrlRequestProcessManager:
    def __init__(self, target: Callable, *args):
        """
        Params:
          - target: the function you want to call
          - *args: list of the arguments you will call the function with
        """
        self.parent_conn, self.child_conn = Pipe()
        self.childProcessStop = Event()
        self.childProcess = Process(
            target=target, args=(self.child_conn, self.childProcessStop, *args)
        )
        self.childProcess.start()


class PortalSimulationData:
    """
    Container for simulation data.
    """

    def __init__(self):
        self.counter = 0
        self.portal_runid: str | None = None
        """Locally determined portal runid, also sent to the portal."""
        self.parent_portal_runid: str | None = None
        """Parent portal runid, derived from locally determined portal runid. Should explicitly be None (not empty string) if not set."""
        self.sim_name = ''
        self.sim_root = ''
        self.phys_time_stamp = -1
        self.monitor_url = ''


class PortalBridge(Component):
    """
    Framework component to communicate with the IPS web portal.
    """

    def __init__(self, services, config):
        """
        Declaration of private variables and initialization of
        :py:class:`component.Component` object.
        """
        super().__init__(services, config)

        self.sim_map: dict[str, PortalSimulationData] = {}
        self.done = False
        self.first_portal_runid = None
        self.portal_url = ''
        self.first_event = True
        self.childProcess = None
        self.childProcessStop = None
        self.parent_conn = None
        self.url_manager_jupyter_notebook = None
        self.url_manager_jupyter_data = None
        self.url_manager_ensemble_uploads = None

    ### COMPONENT FUNCTIONS (public) ###

    def init(self, timestamp=0.0, **keywords):
        """
        Try to connect to the portal, subscribe to *_IPS_MONITOR* events and
        register callback :py:meth:`.process_event`.
        """
        try:
            self.portal_url = self.PORTAL_URL
        except AttributeError:
            pass
        try:
            self.portal_api_key = self._IPS_PORTAL_API_KEY
        except AttributeError:
            pass

        # logging configuration
        if self.services.fwk.log_level == logging.DEBUG:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        _portal_logger.setLevel(log_level)
        log_file = Path(self.services.get_working_dir()) / 'portal.log'
        formatter = logging.Formatter('%(asctime)s %(name)-15s %(levelname)-8s %(message)s')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        _portal_logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        _portal_logger.addHandler(console_handler)

        self.services.subscribe('_IPS_MONITOR', 'process_event')

    def step(self, timestamp=0.0, **keywords):
        """
        Poll for events.
        """
        while not self.done:
            self.services.process_events()
            self._check_url_manager_responses()
            time.sleep(0.5)

    def finalize(self, timestamp=0.0, **keywords):
        pass

    def terminate(self, status: Literal[0, 1]):
        """
        Clean up services and call :py:obj:`sys_exit`.
        """
        if self.childProcess:
            self.childProcess.terminate()
        if self.url_manager_jupyter_data:
            self.url_manager_jupyter_data.childProcess.terminate()
        if self.url_manager_jupyter_notebook:
            self.url_manager_jupyter_notebook.childProcess.terminate()
        if self.url_manager_ensemble_uploads:
            self.url_manager_ensemble_uploads.childProcess.terminate()

        Component.terminate(self, status)

    ### SUBSCRIPTION CHANNELS (public) ###

    def process_event(self, topic_name, the_event):
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
        portal_data['component_id'] = event_body.get('component_id', '')

        event_type = portal_data['eventtype']

        if event_type == 'IPS_START':
            sim_root = event_body['sim_root']
            self.init_simulation(sim_name, sim_root, portal_data['portal_runid'])

        sim_data = self.sim_map[sim_name]
        if event_type == 'PORTALBRIDGE_UPDATE_TIMESTAMP':
            sim_data.phys_time_stamp = portal_data['phystimestamp']
            return
        else:
            portal_data['phystimestamp'] = sim_data.phys_time_stamp

        ### Portal data events ###

        if event_type == 'PORTAL_REGISTER_NOTEBOOK':
            with open(portal_data['data_source'], 'rb') as f:
                portal_data['data'] = f.read()
            self._send_jupyter_notebook(sim_data, portal_data)
            return

        if event_type == 'PORTAL_ADD_JUPYTER_DATA':
            data_source = portal_data['data_source']
            if os.path.isdir(data_source):
                # assume that we are handling a specialized data format, and do not use compression
                # write it into a file to handle chunked uploads
                tarpath = f'{data_source}.tar'
                portal_data['data_archive_format'] = 'tar'
                with tarfile.open(tarpath, 'w') as tar:
                    tar.add(data_source, arcname=os.path.basename(data_source))
                portal_data['data_source'] = tarpath

            self._send_notebook_data(sim_data, portal_data)
            return

        if event_type == 'PORTAL_UPLOAD_ENSEMBLE_PARAMS':
            self._send_ensemble_variables(sim_data, portal_data)
            return

        portal_data['portal_runid'] = sim_data.portal_runid

        if event_type == 'IPS_SET_MONITOR_URL':
            sim_data.monitor_url = portal_data['vizurl']
        elif sim_data.monitor_url:
            portal_data['vizurl'] = sim_data.monitor_url

        if event_type == 'IPS_START' and 'parent_portal_runid' not in portal_data:
            portal_data['parent_portal_runid'] = sim_data.parent_portal_runid
        portal_data['seqnum'] = sim_data.counter

        if 'trace' in portal_data:
            portal_data['trace']['traceId'] = hashlib.md5(
                sim_data.portal_runid.encode()
            ).hexdigest()

        if self.portal_url:
            polling_timeout = 0.0
            if self.first_event:  # First time, launch sendPost.py daemon
                self.parent_conn, child_conn = Pipe()
                self.childProcessStop = Event()
                self.childProcess = Process(
                    target=send_post,
                    args=(child_conn, self.childProcessStop, self.portal_url),
                )
                self.childProcess.start()
                self.first_event = False
                polling_timeout = 5.0  # wait a little longer if this was the first event

            try:
                self.parent_conn.send(portal_data)
            except OSError:
                pass

            self._check_send_post_responses(polling_timeout)

        if event_type == 'IPS_END':
            del self.sim_map[sim_name]

        if len(self.sim_map) == 0:
            self.done = True
            if self.childProcess:
                self.childProcessStop.set()
                self.childProcess.join()
                self._check_send_post_responses(0.0)
            self.services.debug('No more simulation to monitor - exiting')
            time.sleep(1)

    ### LOCAL FUNCTIONS (private) ###

    def _check_send_post_responses(self, polling_timeout: float = 0.0):
        if self.parent_conn is None:
            self.services.warning('Giving up on polling for portal responses')
            return
        while self.parent_conn.poll(timeout=polling_timeout):
            try:
                _msg_type, _component_id, code, msg = self.parent_conn.recv()
            except (EOFError, OSError):
                break

            if code >= 400:
                self.services.error('Portal Error: %d %s', code, msg)
            elif code == -1:
                # disable portal, stop trying to send more data
                self.portal_url = ''
                self.services.error('Disabling portal because: %s', msg)
            else:
                self.services.debug('Portal Response: %d %s', code, msg)
                try:
                    data = json.loads(msg)
                    if 'runid' in data and 'simname' in data:
                        # Indicates IPS-START event return
                        self.services.info(
                            'Run Portal URL = %s/%s',
                            self.portal_url,
                            data.get('runid'),
                        )
                        self.services.set_config_param(
                            '_IPS_PORTAL_RUNID',
                            str(data.get('runid')),
                            target_sim_name=data.get('simname'),
                        )
                except (TypeError, json.decoder.JSONDecodeError):
                    pass

    def _check_url_manager_responses(self):
        """poll all data API checks"""
        for manager in [
            self.url_manager_jupyter_notebook,
            self.url_manager_jupyter_data,
            self.url_manager_ensemble_uploads,
        ]:
            if manager is None:
                continue
            while manager.parent_conn.poll():
                try:
                    msg_type, component_id, code, msg = manager.parent_conn.recv()
                except (EOFError, OSError):
                    break

                if code >= 400:
                    self.services.error('Portal Error: %d %s', code, msg)
                elif code == -1:
                    # disable portal, stop trying to send more data
                    self.portal_url = ''
                    self.services.error('Disabling portal because: %s', msg)
                else:
                    self.services.debug('Portal Response: %d %s', code, msg)
                    if msg_type == ENSEMBLE_MESSAGE_TYPE:
                        self.services.publish(
                            f'_IPS_{component_id}',
                            '_IPS_PORTAL_UPLOAD_ENSEMBLE_PARAMS_SUCCESS',
                            'true',
                        )

    def _send_jupyter_notebook(self, sim_data: PortalSimulationData, event_data):
        if self.portal_url and self.portal_api_key:
            if not self.url_manager_jupyter_notebook:
                self.url_manager_jupyter_notebook = UrlRequestProcessManager(
                    send_jupyter_notebook,
                    self.portal_url + '/api/data/add_notebook',
                    self.portal_api_key,
                    self.USER,
                )
            try:
                self.url_manager_jupyter_notebook.parent_conn.send(event_data)
            except OSError:
                self.services.error('Failed to send notebook to portal %s', event_data)

    def _send_notebook_data(self, sim_data: PortalSimulationData, event_data):
        if self.portal_url and self.portal_api_key:
            if not self.url_manager_jupyter_data:
                self.url_manager_jupyter_data = UrlRequestProcessManager(
                    send_jupyter_notebook_data,
                    self.portal_url + '/api/data/add_data_file',
                    self.portal_api_key,
                    self.USER,
                )
            try:
                self.url_manager_jupyter_data.parent_conn.send(event_data)
            except OSError:
                self.services.error('Failed to send notebook data to portal %s', event_data)

    def _send_ensemble_variables(self, sim_data: PortalSimulationData, event_data):
        if self.portal_url and self.portal_api_key:
            if not self.url_manager_ensemble_uploads:
                self.url_manager_ensemble_uploads = UrlRequestProcessManager(
                    send_ensemble_variables,
                    self.portal_url + '/api/data/add_ensemble_variables',
                    self.portal_api_key,
                    self.USER,
                )
            try:
                self.url_manager_ensemble_uploads.parent_conn.send(event_data)
            except OSError:
                self.services.error('Failed to send ensemble variables to portal %s', event_data)

    def init_simulation(self, sim_name: str, sim_root: str, portal_runid: str):
        """
        Create and send information about simulation *sim_name* living in
        *sim_root* so the portal can set up corresponding structures to manage
        data from the sim.
        """
        self.services.debug(
            'Initializing simulation using PortalBridge: %s -- %s ',
            sim_name,
            sim_root,
        )
        if hasattr(self, '_IPS_PORTAL_API_KEY'):
            self.services.set_config_param(
                '_IPS_PORTAL_API_KEY',
                self._IPS_PORTAL_API_KEY,
                target_sim_name=sim_name,
            )

        sim_data = PortalSimulationData()
        sim_data.sim_name = sim_name
        sim_data.sim_root = sim_root

        sim_data.portal_runid = portal_runid
        try:
            self.services.set_config_param(
                'PORTAL_RUNID', sim_data.portal_runid, target_sim_name=sim_name
            )
        except Exception:
            self.services.error('Simulation %s is not accessible', sim_name)
            return

        if self.first_portal_runid:
            sim_data.parent_portal_runid = self.first_portal_runid
        else:
            self.first_portal_runid = sim_data.portal_runid

        self.sim_map[sim_name] = sim_data
