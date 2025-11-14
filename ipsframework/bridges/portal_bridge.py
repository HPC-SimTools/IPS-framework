# -------------------------------------------------------------------------------
# Copyright 2006-2022 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import hashlib
import json
import os
import tarfile
import time
from multiprocessing import Event, Pipe, Process
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event as EventType
from typing import Any, Callable, Literal

import urllib3

from ipsframework import Component
from ipsframework.bridges.local_event_logger import LocalEventLogger, SimulationData


def send_post(conn: Connection, stop: EventType, url: str):
    fail_count = 0

    http = urllib3.PoolManager(retries=urllib3.util.Retry(3, backoff_factor=0.25), headers={'Content-Type': 'application/json'})

    while True:
        if conn.poll(0.1):
            msgs = []
            while conn.poll(0.01):
                msgs.append(conn.recv())
            try:
                resp = http.request('POST', url, body=json.dumps(msgs).encode())
            except urllib3.exceptions.MaxRetryError as e:
                fail_count += 1
                conn.send((999, str(e)))
            else:
                conn.send((resp.status, resp.data.decode()))
                fail_count = 0

            if fail_count >= 3:
                conn.send((-1, 'Too many consecutive failed connections'))
                break
        elif stop.is_set():
            break


def send_jupyter_notebook(conn: Connection, stop: EventType, url: str, api_key: str, username: str):
    fail_count = 0

    http = urllib3.PoolManager(retries=urllib3.util.Retry(3, backoff_factor=0.25))

    while True:
        if conn.poll(0.1):
            next_val: dict[str, Any] = conn.recv()
            # TODO - consider using multipart/form-data instead
            try:
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
            except urllib3.exceptions.MaxRetryError as e:
                fail_count += 1
                conn.send((999, str(e)))
            else:
                conn.send((resp.status, resp.data.decode()))
                fail_count = 0

            if fail_count >= 3:
                conn.send((-1, 'Too many consecutive failed connections'))
                break
        elif stop.is_set():
            break


def send_jupyter_notebook_data(conn: Connection, stop: EventType, url: str, api_key: str, username: str):
    fail_count = 0

    http = urllib3.PoolManager(retries=urllib3.util.Retry(3, backoff_factor=0.25))

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
                resp = http.request(
                    'POST',
                    url,
                    body=body,
                    headers=headers,
                )
            except (urllib3.exceptions.MaxRetryError, OSError) as e:
                fail_count += 1
                conn.send((999, str(e)))
            else:
                conn.send((resp.status, resp.data.decode()))
                fail_count = 0

            if fail_count >= 3:
                conn.send((-1, 'Too many consecutive failed connections'))
                break
        elif stop.is_set():
            break


def send_ensemble_variables(conn: Connection, stop: EventType, url: str, api_key: str, username: str):
    fail_count = 0

    http = urllib3.PoolManager(retries=urllib3.util.Retry(3, backoff_factor=0.25))

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
                resp = http.request(
                    'POST',
                    url,
                    body=body,
                    headers=headers,
                )
            except (urllib3.exceptions.MaxRetryError, OSError) as e:
                fail_count += 1
                conn.send((999, str(e)))
            else:
                conn.send((resp.status, resp.data.decode()))
                fail_count = 0

            if fail_count >= 3:
                conn.send((-1, 'Too many consecutive failed connections'))
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
        self.childProcess = Process(target=target, args=(self.child_conn, self.childProcessStop, *args))
        self.childProcess.start()


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
        self.sim_map: dict[str, SimulationData] = {}
        self.done = False
        self.local_event_logger = LocalEventLogger()
        self.portal_url = ''
        self.first_event = True
        self.childProcess = None
        self.childProcessStop = None
        self.parent_conn = None
        self.url_manager_jupyter_notebook = None
        self.url_manager_jupyter_data = None
        self.url_manager_ensemble_uploads = None

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

    def process_event(self, topicName, theEvent):
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
            with open(portal_data['data_source'], 'rb') as f:
                portal_data['data'] = f.read()
            self.send_jupyter_notebook(sim_data, portal_data)
            return

        if portal_data['eventtype'] == 'PORTAL_ADD_JUPYTER_DATA':
            data_source = portal_data['data_source']
            if os.path.isdir(data_source):
                # assume that we are handling a specialized data format, and do not use compression
                # write it into a file to handle chunked uploads
                tarpath = f'{data_source}.tar'
                portal_data['data_archive_format'] = 'tar'
                with tarfile.open(tarpath, 'w') as tar:
                    tar.add(data_source, arcname=os.path.basename(data_source))
                portal_data['data_source'] = tarpath

            self.send_notebook_data(sim_data, portal_data)
            return

        if portal_data['eventtype'] == 'PORTAL_UPLOAD_ENSEMBLE_PARAMS':
            self.send_ensemble_variables(sim_data, portal_data)
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

        if self.portal_url:
            if self.first_event:  # First time, launch sendPost.py daemon
                self.parent_conn, child_conn = Pipe()
                self.childProcessStop = Event()
                self.childProcess = Process(target=send_post, args=(child_conn, self.childProcessStop, self.portal_url))
                self.childProcess.start()
                self.first_event = False

            try:
                self.parent_conn.send(portal_data)
            except OSError:
                pass

            self.check_send_post_responses()

        if portal_data['eventtype'] == 'IPS_END':
            del self.sim_map[sim_name]

        if len(self.sim_map) == 0:
            if self.childProcess:
                self.childProcessStop.set()
                self.childProcess.join()
                self.check_send_post_responses()
            self.done = True
            self.services.debug('No more simulation to monitor - exiting')
            time.sleep(1)

    def check_send_post_responses(self):
        while self.parent_conn.poll():
            try:
                code, msg = self.parent_conn.recv()
            except (EOFError, OSError):
                break

            try:
                data = json.loads(msg)
                if 'runid' in data and 'simname' in data:
                    # Indicates IPS-START event return
                    self.services.info('Run Portal URL = %s/%s', self.portal_url, data.get('runid'))
                    self.services.set_config_param('_IPS_PORTAL_RUNID', str(data.get('runid')), target_sim_name=data.get('simname'))

                msg = json.dumps(data)
            except (TypeError, json.decoder.JSONDecodeError):
                pass
            if code >= 400:
                self.services.error('Portal Error: %d %s', code, msg)
            elif code == -1:
                # disable portal, stop trying to send more data
                self.portal_url = ''
                self.services.error('Disabling portal because: %s', msg)
            else:
                self.services.debug('Portal Response: %d %s', code, msg)

    def http_req_and_response(self, manager: UrlRequestProcessManager, event_data):
        try:
            manager.parent_conn.send(event_data)
        except OSError:
            pass

        while manager.parent_conn.poll():
            try:
                code, msg = manager.parent_conn.recv()
            except (EOFError, OSError):
                break

            if code == -1:
                # disable portal, stop trying to send more data
                self.portal_url = ''
                self.services.error('Disabling portal because: %s', msg)
            elif code >= 400:
                self.services.error('Portal Error: %d %s', code, msg)
            else:
                self.services.debug('Portal Response: %d %s', code, msg)

    def send_jupyter_notebook(self, sim_data: SimulationData, event_data):
        if self.portal_url and self.portal_api_key:
            if not self.url_manager_jupyter_notebook:
                self.url_manager_jupyter_notebook = UrlRequestProcessManager(
                    send_jupyter_notebook, self.portal_url + '/api/data/add_notebook', self.portal_api_key, self.USER
                )
            self.http_req_and_response(self.url_manager_jupyter_notebook, event_data)

    def send_notebook_data(self, sim_data: SimulationData, event_data):
        if self.portal_url and self.portal_api_key:
            if not self.url_manager_jupyter_data:
                self.url_manager_jupyter_data = UrlRequestProcessManager(
                    send_jupyter_notebook_data, self.portal_url + '/api/data/add_data_file', self.portal_api_key, self.USER
                )
            self.http_req_and_response(self.url_manager_jupyter_data, event_data)

    def send_ensemble_variables(self, sim_data: SimulationData, event_data):
        if self.portal_url and self.portal_api_key:
            if not self.url_manager_ensemble_uploads:
                self.url_manager_ensemble_uploads = UrlRequestProcessManager(
                    send_ensemble_variables, self.portal_url + '/api/data/add_ensemble_variables', self.portal_api_key, self.USER
                )
            self.http_req_and_response(self.url_manager_ensemble_uploads, event_data)

    def init_simulation(self, sim_name: str, sim_root: str):
        """
        Create and send information about simulation *sim_name* living in
        *sim_root* so the portal can set up corresponding structures to manage
        data from the sim.
        """
        self.services.debug('Initializing simulation using PortalBridge: %s -- %s ', sim_name, sim_root)
        if hasattr(self, '_IPS_PORTAL_API_KEY'):
            self.services.set_config_param('_IPS_PORTAL_API_KEY', self._IPS_PORTAL_API_KEY, target_sim_name=sim_name)

        sim_data = self.local_event_logger.init_simulation(self.services, sim_name, sim_root, self.HOST, self.USER)
        self.sim_map[sim_data.sim_name] = sim_data

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
