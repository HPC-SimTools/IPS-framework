import glob
import json
import hashlib
from ipsframework import Framework


def write_basic_config_and_platform_files(tmpdir, timeout='', logfile='', errfile='', nproc=1, exe='/bin/sleep', value='', shifter=False):
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

    config = f"""RUN_COMMENT = trace testing
SIM_NAME = trace
LOG_FILE = {str(tmpdir)}/sim.log
LOG_LEVEL = INFO
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
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
    MODULE = components.drivers.driver_double_trace
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


def test_trace_info(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, value=1)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check simulation_log, make sure it includes events from dask tasks
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        lines = json_file.readlines()
    lines = [json.loads(line.strip()) for line in lines]
    assert len(lines) == 17

    portal_runid = lines[0]['portal_runid']

    traces = [e['trace'] for e in lines if "trace" in e]

    assert len(traces) == 8

    call_ids = [5, 1, 8, 2, 9, 7, 10, None]
    service_names = ['trace@driver@1',
                     '/bin/sleep',
                     'trace@simple_sleep@2',
                     '/bin/sleep',
                     'trace@simple_sleep@2',
                     'trace@driver@1',
                     'trace@driver@1',
                     'trace@FRAMEWORK@Framework@0']
    names = ['init(0)',
             '1',
             'step(0)',
             '1',
             'step(0)',
             'step(0)',
             'finalize(0)',
             None]
    tags = [None,
            {"procs_requested": "1",  "cores_allocated": "1"},
            {},
            {"procs_requested": "1",  "cores_allocated": "1"},
            {},
            None,
            None,
            {'total_cores': '2'}]
    parents = [7, 2, 5, 4, 5, 7, 7, None]

    for n, trace in enumerate(traces):
        assert isinstance(trace['timestamp'], int)
        assert isinstance(trace['duration'], int)
        assert trace['traceId'] == hashlib.md5(portal_runid.encode()).hexdigest()
        assert trace['localEndpoint']['serviceName'] == service_names[n]
        assert "id" in trace
        assert trace.get('tags') == tags[n]

        if names[n]:
            assert trace['name'] == names[n]
            assert trace['id'] == hashlib.md5(f"{trace['localEndpoint']['serviceName']}:{trace['name']}:{call_ids[n]}".encode()).hexdigest()[:16]
        else:
            assert trace['id'] == hashlib.md5(f"{trace['localEndpoint']['serviceName']}".encode()).hexdigest()[:16]

        if parents[n]:
            if names[parents[n]]:
                assert trace['parentId'] == hashlib.md5(f"{service_names[parents[n]]}:{names[parents[n]]}:{call_ids[parents[n]]}".encode()).hexdigest()[:16]
            else:
                assert trace['parentId'] == hashlib.md5(f"{service_names[parents[n]]}".encode()).hexdigest()[:16]
