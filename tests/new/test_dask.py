import pytest
import glob
import json
from ipsframework import Framework


def write_basic_config_and_platform_files(tmpdir, timeout='', logfile='', errfile='', nproc=1, exe='/bin/sleep', value=''):
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

    config = f"""RUN_COMMENT = testing
SIM_NAME = test
LOG_FILE = {str(tmpdir)}/sim.log
LOG_LEVEL = INFO
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
[PORTS]
    NAMES = DRIVER DASK
    [[DRIVER]]
      IMPLEMENTATION = DRIVER
    [[DASK]]
      IMPLEMENTATION = DASK
[DRIVER]
    CLASS = DRIVER
    SUB_CLASS =
    NAME = driver
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.drivers.driver
[DASK]
    CLASS = DASK
    SUB_CLASS =
    NAME = dask_worker
    BIN_PATH =
    EXECUTABLE = {exe}
    VALUE = {value}
    NPROC = {nproc}
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.workers.dask_worker
    TIMEOUT = {timeout}
    LOGFILE = {logfile}
    ERRFILE = {errfile}
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_dask(tmpdir):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, value=1)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    log = "DASK__dask_worker_2 INFO     {}\n"
    assert log.format("cmd = /bin/sleep") in lines
    assert log.format("ret_val = 4") in lines

    # task successful and return 0
    for i in range(4):
        assert log.format(f"task_{i} 0") in lines

    # check simulation_log, make sure it includes events from dask tasks
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        lines = json_file.readlines()
    lines = [json.loads(line.strip()) for line in lines]
    assert len(lines) == 22

    eventtypes = [e.get('eventtype') for e in lines]
    assert eventtypes.count('IPS_LAUNCH_DASK_TASK') == 4
    assert eventtypes.count('IPS_TASK_END') == 5

    launch_dask_comments = [e.get('comment') for e in lines if e.get('eventtype') == "IPS_LAUNCH_DASK_TASK"]
    for task in range(4):
        assert f'task_name = task_{task}, Target = /bin/sleep 1' in launch_dask_comments

    task_end_comments = [e.get('comment')[:-4] for e in lines if e.get('eventtype') == "IPS_TASK_END"]
    for task in range(4):
        assert f'task_name = task_{task}, elasped time = 1' in task_end_comments


def test_dask_timeout(tmpdir):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, timeout=1, value=100)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    log = "DASK__dask_worker_2 INFO     {}\n"
    assert log.format("cmd = /bin/sleep") in lines
    assert log.format("ret_val = 4") in lines

    # task timeouted and return -1
    for i in range(4):
        assert log.format(f"task_{i} -1") in lines

    # check simulation_log, make sure it includes events from dask tasks
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        lines = json_file.readlines()
    lines = [json.loads(line.strip()) for line in lines]
    assert len(lines) == 22

    eventtypes = [e.get('eventtype') for e in lines]
    assert eventtypes.count('IPS_LAUNCH_DASK_TASK') == 4
    assert eventtypes.count('IPS_TASK_END') == 5

    launch_dask_comments = [e.get('comment') for e in lines if e.get('eventtype') == "IPS_LAUNCH_DASK_TASK"]
    for task in range(4):
        assert f'task_name = task_{task}, Target = /bin/sleep 100' in launch_dask_comments

    task_end_comments = [e.get('comment') for e in lines if e.get('eventtype') == "IPS_TASK_END"]
    for task in range(4):
        assert f'task_name = task_{task}, timed-out after 1.0s' in task_end_comments


def test_dask_nproc(tmpdir):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, nproc=2, value=1)

    # Running with NPROC=2 should prevent dask from running and revert to normal task pool

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    log = "DASK__dask_worker_2 INFO     {}\n"
    assert log.format("cmd = /bin/sleep") in lines
    assert log.format("ret_val = 4") in lines

    # task timeouted and return -1
    for i in range(4):
        assert log.format(f"task_{i} 0") in lines

    # check for warning message that dask isn't being used
    assert "DASK__dask_worker_2 WARNING  Requested use_dask but cannot because multiple processors requested\n" in lines


def test_dask_logfile(tmpdir):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")

    exe = tmpdir.join("stdouterr_write.sh")
    exe.write("#!/bin/bash\necho Running $1\n>&2 echo ERROR $1\n")
    exe.chmod(448)  # 700

    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, exe=str(exe), logfile='task_{}.log')

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    log = "DASK__dask_worker_2 INFO     {}\n"
    assert log.format(f"cmd = {exe}") in lines
    assert log.format("ret_val = 4") in lines

    # task successful and return 0
    for i in range(4):
        assert log.format(f"task_{i} 0") in lines

    # check that the process output log files are created
    work_dir = tmpdir.join("work").join("DASK__dask_worker_2")
    for i in range(4):
        log_file = work_dir.join(f"task_{i}.log")
        assert log_file.exists()
        lines = log_file.readlines()
        assert len(lines) == 2
        assert lines[0] == f'Running {i}\n'
        assert lines[1] == f'ERROR {i}\n'


def test_dask_logfile_errfile(tmpdir):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")

    exe = tmpdir.join("stdouterr_write.sh")
    exe.write("#!/bin/bash\necho Running $1\n>&2 echo ERROR $1\n")
    exe.chmod(448)  # 700
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, exe=str(exe),
                                                                       logfile='task_{}.log', errfile='task_{}.err')

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    log = "DASK__dask_worker_2 INFO     {}\n"
    assert log.format(f"cmd = {exe}") in lines
    assert log.format("ret_val = 4") in lines

    # task successful and return 0
    for i in range(4):
        assert log.format(f"task_{i} 0") in lines

    # check that the process output log files are created
    work_dir = tmpdir.join("work").join("DASK__dask_worker_2")
    for i in range(4):
        log_file = work_dir.join(f"task_{i}.log")
        assert log_file.exists()
        lines = log_file.readlines()
        assert len(lines) == 1
        assert lines[0] == f'Running {i}\n'
        err_file = work_dir.join(f"task_{i}.err")
        assert err_file.exists()
        lines = err_file.readlines()
        assert len(lines) == 1
        assert lines[0] == f'ERROR {i}\n'
