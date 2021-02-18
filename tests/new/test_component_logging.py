from ipsframework import Framework


map_log_to_level = {"log": "INFO",
                    "debug": "DEBUG",
                    "info": "INFO",
                    "warning": "WARNING",
                    "error": "ERROR",
                    "exception": "ERROR",
                    "critical": "CRITICAL"}


def write_basic_config_and_platform_files(tmpdir, debug=False):
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

    log_level = "DEBUG" if debug else "WARNING"

    config = f"""RUN_COMMENT = testing
SIM_NAME = test
LOG_FILE = {str(tmpdir)}/sim.log
LOG_LEVEL = {log_level}
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
[PORTS]
    NAMES = DRIVER
    [[DRIVER]]
      IMPLEMENTATION = LOGGING_DRIVER
[LOGGING_DRIVER]
    CLASS = LOGGING
    SUB_CLASS =
    NAME = logging_tester
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.drivers.logging_tester
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_component_logging(tmpdir, capfd):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

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

    component_id = "LOGGING__logging_tester_1"

    # for log_level=WARNING only WARNING, ERROR and CRITICAL logs should be included
    # DEBUG and INFO should be excluded
    for method in ["init", "step", "finalize"]:
        for log_type in ["warning", "error", "exception", "critical"]:
            assert f'{component_id} {map_log_to_level[log_type]:8} {method} msg: {log_type}\n' in lines
        for log_type in ["log", "debug", "info"]:
            assert f'{component_id} {map_log_to_level[log_type]:8} {method} msg: {log_type}\n' not in lines

    # check message formatting with arguments
    for log_type in ["warning", "error", "exception", "critical"]:
        assert f'{component_id} {map_log_to_level[log_type]:8} step msg: {log_type} timestamp=0 test\n' in lines
    for log_type in ["log", "debug", "info"]:
        assert f'{component_id} {map_log_to_level[log_type]:8} step msg: {log_type} timestamp=0 test\n' not in lines


def test_component_logging_debug(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir, debug=True)

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

    map_log_to_level = {"log": "INFO",
                        "debug": "DEBUG",
                        "info": "INFO",
                        "warning": "WARNING",
                        "error": "ERROR",
                        "exception": "ERROR",
                        "critical": "CRITICAL"}

    component_id = "LOGGING__logging_tester_1"

    # for log_level=DEBUG all logs should be included
    for method in ["init", "step", "finalize"]:
        for log_type in ["log", "debug", "info", "warning", "error", "exception", "critical"]:
            assert f'{component_id} {map_log_to_level[log_type]:8} {method} msg: {log_type}\n' in lines

    # check message formatting with arguments
    for log_type in ["log", "debug", "info", "warning", "error", "exception", "critical"]:
        assert f'{component_id} {map_log_to_level[log_type]:8} step msg: {log_type} timestamp=0 test\n' in lines
