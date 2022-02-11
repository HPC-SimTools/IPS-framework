import glob
import json
import os
import importlib
import shutil
import pytest
import ipsframework
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
    SHIFTER = {shifter}
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
    assert len(lines) == 25

    eventtypes = [e.get('eventtype') for e in lines]
    assert eventtypes.count('IPS_LAUNCH_DASK_TASK') == 4
    assert eventtypes.count('IPS_TASK_END') == 5

    launch_dask_comments = [e.get('comment') for e in lines if e.get('eventtype') == "IPS_LAUNCH_DASK_TASK"]
    for task in range(4):
        assert f'task_name = task_{task}, Target = /bin/sleep 1' in launch_dask_comments

    task_end_comments = [e.get('comment')[:-4] for e in lines if e.get('eventtype') == "IPS_TASK_END"]
    for task in range(4):
        assert f'task_name = task_{task}, elapsed time = 1' in task_end_comments


@pytest.mark.skipif(shutil.which('shifter') is not None,
                    reason="This tests only works if shifter doesn't exist")
def test_dask_shifter_fail(tmpdir):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, value=1, shifter=True)

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

    assert "DASK__dask_worker_2 ERROR    Requested to run dask within shifter but shifter not available\n" in lines

    # check simulation_log, make sure it includes events from dask tasks
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        lines = json_file.readlines()
    lines = [json.loads(line.strip()) for line in lines]
    assert len(lines) == 10

    assert lines[-1].get('eventtype') == "IPS_END"
    assert lines[-1].get('comment') == "Simulation Execution Error"


def test_dask_fake_shifter(tmpdir, monkeypatch):
    pytest.importorskip("dask")
    pytest.importorskip("distributed")

    shifter = tmpdir.join("shifter")
    shifter.write("#!/bin/bash\necho Running $@ in shifter >> shifter.log\n$@\n")
    shifter.chmod(448)  # 700

    old_PATH = os.environ['PATH']
    monkeypatch.setenv("PATH", str(tmpdir), prepend=os.pathsep)
    # need to reimport to get fake shifter
    importlib.reload(ipsframework.services)

    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, value=1, shifter=True)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    monkeypatch.setenv("PATH", old_PATH)
    # need to reimport to remove fake shifter
    importlib.reload(ipsframework.services)

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
    assert len(lines) == 25

    eventtypes = [e.get('eventtype') for e in lines]
    assert eventtypes.count('IPS_LAUNCH_DASK_TASK') == 4
    assert eventtypes.count('IPS_TASK_END') == 5

    launch_dask_comments = [e.get('comment') for e in lines if e.get('eventtype') == "IPS_LAUNCH_DASK_TASK"]
    for task in range(4):
        assert f'task_name = task_{task}, Target = /bin/sleep 1' in launch_dask_comments

    task_end_comments = [e.get('comment')[:-4] for e in lines if e.get('eventtype') == "IPS_TASK_END"]
    for task in range(4):
        assert f'task_name = task_{task}, elapsed time = 1' in task_end_comments

    # check shifter.log file
    with open(str(tmpdir.join('/work/DASK__dask_worker_2').join('shifter.log')), 'r') as f:
        lines = sorted(f.readlines())

    assert lines[0].startswith('Running dask-scheduler --no-dashboard --scheduler-file')
    assert lines[0].endswith('--port 0 in shifter\n')
    assert lines[1].startswith('Running dask-worker --scheduler-file')
    assert lines[1].endswith('--nprocs 1 --nthreads 0 --no-dashboard in shifter\n')


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
    assert len(lines) == 25

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


@pytest.mark.cori
def test_dask_shifter_on_cori(tmpdir):
    """
    This test requires the shifter image to be set. e.g.

    #SBATCH --image=continuumio/anaconda3:2020.11
    """
    exe = tmpdir.join("shifter_env.sh")
    exe.write("#!/bin/bash\necho Running $1\necho SHIFTER_RUNTIME=$SHIFTER_RUNTIME\necho SHIFTER_IMAGEREQUEST=$SHIFTER_IMAGEREQUEST\n")
    exe.chmod(448)  # 700

    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, exe=str(exe),
                                                                       logfile='task_{}.log',
                                                                       shifter=True)

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
        assert len(lines) == 3
        assert lines[0] == f'Running {i}\n'
        assert lines[1] == 'SHIFTER_RUNTIME=1\n'
        assert lines[2].startswith("SHIFTER_IMAGEREQUEST")
