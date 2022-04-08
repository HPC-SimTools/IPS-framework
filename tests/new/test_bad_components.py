from ipsframework import Framework


def write_basic_config_and_platform_files(tmpdir, worker):
    platform_file = tmpdir.join('platform.conf')

    platform = """MPIRUN = eval
NODE_DETECTION = manual
CORES_PER_NODE = 1
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
    MODULE = components.drivers.driver
[WORKER]
    CLASS = WORKER
    SUB_CLASS =
    NAME = {worker}
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.workers.bad_workers
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_exception(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, worker='exception_worker')

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

    assert "RuntimeError: Runtime error\n" in lines
    assert "Exception: Runtime error\n" in lines

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert "WORKER__exception_worker_2 ERROR    Uncaught Exception in component method.\n" in lines
    assert "DRIVER__driver_1 ERROR    Uncaught Exception in component method.\n" in lines


def test_bad_task(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, worker='bad_task_worker')

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

    assert "ValueError: task binary of wrong type, expected str but found int\n" in lines
    assert "Exception: task binary of wrong type, expected str but found int\n" in lines

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert "WORKER__bad_task_worker_2 ERROR    Uncaught Exception in component method.\n" in lines
    assert "DRIVER__driver_1 ERROR    Uncaught Exception in component method.\n" in lines


def test_bad_task_pool1(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, worker='bad_task_pool_worker1')

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

    assert "ValueError: task task binary of wrong type, expected str but found int\n" in lines
    assert "Exception: task task binary of wrong type, expected str but found int\n" in lines

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert "WORKER__bad_task_pool_worker1_2 ERROR    Uncaught Exception in component method.\n" in lines
    assert "DRIVER__driver_1 ERROR    Uncaught Exception in component method.\n" in lines


def test_bad_task_pool2(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, worker='bad_task_pool_worker2')

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

    assert "ValueError: task task binary of wrong type, expected str but found function\n" in lines
    assert "Exception: task task binary of wrong type, expected str but found function\n" in lines

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert "WORKER__bad_task_pool_worker2_2 ERROR    Uncaught Exception in component method.\n" in lines
    assert "DRIVER__driver_1 ERROR    Uncaught Exception in component method.\n" in lines


def test_assign_protected_attribute(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, worker='assign_protected_attribute')

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

    # python 3.10 includes the attribute name in the error message
    assert "AttributeError: can't set attribute\n" in lines or "AttributeError: can't set attribute 'args'\n" in lines
    assert "Exception: can't set attribute\n" in lines or "Exception: can't set attribute 'args'\n" in lines

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert "WORKER__assign_protected_attribute_2 ERROR    Uncaught Exception in component method.\n" in lines
    assert "DRIVER__driver_1 ERROR    Uncaught Exception in component method.\n" in lines
