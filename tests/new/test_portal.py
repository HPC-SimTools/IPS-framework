import hashlib
import json
import sys
from multiprocessing import Process, set_start_method

import pytest

from ipsframework import Framework

# Try using fork for starting subprocesses, this is the default on
# Linux but not macOS with python >= 3.8
if sys.platform == 'darwin':
    try:
        set_start_method('fork')
    except RuntimeError:
        # context can only be set once
        pass


def write_basic_config_and_platform_files(tmpdir):
    platform_file = tmpdir.join('platform.conf')

    platform = """MPIRUN = eval
NODE_DETECTION = manual
CORES_PER_NODE = 2
SOCKETS_PER_NODE = 1
NODE_ALLOCATION_MODE = shared
HOST =
SCRATCH =
"""

    with open(platform_file, 'w') as f:
        f.write(platform)

    config_file = tmpdir.join('ips.config')

    config = f"""RUN_COMMENT = portal testing
SIM_NAME = portal_test
LOG_FILE = {tmpdir!s}/sim.log
LOG_LEVEL = INFO
SIM_ROOT = {tmpdir!s}
SIMULATION_MODE = NORMAL
USE_PORTAL = True
PORTAL_URL = http://localhost:18080
[PORTS]
    NAMES = DRIVER WORKER
    [[DRIVER]]
      IMPLEMENTATION = DRIVER
    [[WORKER]]
      IMPLEMENTATION = WORKER
[DRIVER]
    CLASS = DRIVER
    SUB_CLASS =
    NAME = driver
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.drivers.simple_driver
[WORKER]
    CLASS = WORKER
    SUB_CLASS =
    NAME = simple_sleep
    NPROC = 1
    BIN_PATH =
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.workers.simple_sleep
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_portal(tmpdir):
    pytest.importorskip('flask')
    from flask import Flask, jsonify, request  # pylint: disable=import-outside-toplevel

    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    # standup simple flask server to test send_post
    def flask_server():
        app = Flask('IPS portal')

        @app.route('/', methods=['POST'])
        def api():
            data = request.get_json()
            return jsonify(message='Events added to run', events=len(data), runid=42, event=data), 200

        app.run(port=18080)

    p = Process(target=flask_server)
    p.start()
    framework = Framework(
        config_file_list=[str(config_file)],
        log_file_name=str(tmpdir.join('ips.log')),
        platform_file_name=str(platform_file),
        debug=True,
        verbose_debug=None,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    p.terminate()

    with open(str(tmpdir.join('ips.log')), 'r') as f:
        lines = f.readlines()

    URLs = [line[57:] for line in lines if 'FWK_COMP_PortalBridge_4 INFO' in line]
    assert len(URLs) > 0
    assert URLs[0] == 'Run Portal URL = http://localhost:18080/42\n'

    # remove timestamp and common start
    lines = [
        (int(code), json.loads(data))
        for (code, data) in [line[74:].strip().split(maxsplit=1) for line in lines if 'FWK_COMP_PortalBridge_4 DEBUG    Portal Response: ' in line]
    ]

    for code, _ in lines:
        assert code == 200

    # check number of events sent to portal
    assert sum(data.get('events') for _, data in lines) == 13
    # get first event to check
    data = lines[0][1]
    assert data['runid'] == 42
    assert data['message'] == 'Events added to run'

    event = data['event'][0]
    assert event['code'] == 'Framework'
    assert event['eventtype'] == 'IPS_START'
    assert event['comment'] == 'Starting IPS Simulation'
    assert event['state'] == 'Running'
    assert event['sim_name'] == 'portal_test'
    assert event['seqnum'] == 0
    assert 'ips_version' in event
    assert 'time' in event

    # get last event to check
    data = lines[-1][1]
    assert data['runid'] == 42
    assert data['message'] == 'Events added to run'

    event = data['event'][-1]
    assert event['code'] == 'Framework'
    assert event['eventtype'] == 'IPS_END'
    assert event['comment'] == 'Simulation Ended'
    assert event['state'] == 'Completed'
    assert event['sim_name'] == 'portal_test'
    assert event['seqnum'] == 12
    assert 'time' in event
    assert 'trace' in event
    trace = event['trace']
    assert 'duration' in trace
    assert 'timestamp' in trace
    assert 'id' in trace
    assert trace['id'] == hashlib.md5('portal_test@FRAMEWORK@Framework@0'.encode()).hexdigest()[:16]
    assert 'traceId' in trace
    assert trace['traceId'] == hashlib.md5(event['portal_runid'].encode()).hexdigest()
    assert 'parentId' not in trace
    assert 'localEndpoint' in trace
    assert trace['localEndpoint']['serviceName'] == 'portal_test@FRAMEWORK@Framework@0'


def test_portal_no_server(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(
        config_file_list=[str(config_file)],
        log_file_name=str(tmpdir.join('ips.log')),
        platform_file_name=str(platform_file),
        debug=None,
        verbose_debug=None,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    with open(str(tmpdir.join('ips.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp and common start
    lines = [line[57:] for line in lines if 'FWK_COMP_PortalBridge_4 ERROR' in line]

    assert len(lines) == 4
    # should fail 3 time then disable the portal
    for n in range(3):
        assert lines[n].startswith('Portal Error: 999 HTTPConnectionPool')

    assert lines[-1] == 'Disabling portal because: Too many consecutive failed connections\n'
