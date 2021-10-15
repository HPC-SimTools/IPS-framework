from ipsframework import Framework
import glob
import json
import pytest


def write_basic_config_and_platform_files(tmpdir):
    test_component = tmpdir.join("test_component.py")

    driver = """#!/usr/bin/env python3
from ipsframework.component import Component
class test_driver(Component):
    def __init__(self, services, config):
        super().__init__(services, config)
"""

    with open(test_component, 'w') as f:
        f.write(driver)

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
LOG_FILE = {str(tmpdir)}/log.warning
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
[PORTS]
    NAMES = DRIVER
    [[DRIVER]]
        IMPLEMENTATION = test_driver
[test_driver]
    CLASS = driver
    SUB_CLASS =
    NAME = test_driver
    NPROC = 1
    BIN_PATH =
    INPUT_DIR =
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT = {test_component}
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_framework_simple(tmpdir, capfd):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    assert framework.log_file_name.endswith('test.log')

    assert len(framework.config_manager.get_framework_components()) == 2

    component_map = framework.config_manager.get_component_map()

    assert len(component_map) == 1
    assert 'test' in component_map
    test = component_map['test']
    assert len(test) == 1
    assert test[0].get_class_name() == 'test_driver'
    assert test[0].get_instance_name().startswith('test@test_driver')
    assert test[0].get_seq_num() == 1
    assert test[0].get_serialization().startswith('test@test_driver')
    assert test[0].get_sim_name() == 'test'

    # check all registered service handlers
    service_handlers = sorted(framework.service_handler.keys())
    assert service_handlers == ['createListener',
                                'create_simulation',
                                'existsTopic',
                                'finish_task',
                                'getSubscription',
                                'getTopic',
                                'get_allocation',
                                'get_config_parameter',
                                'get_port',
                                'get_time_loop',
                                'init_call',
                                'init_task',
                                'init_task_pool',
                                'launch_task',
                                'merge_current_plasma_state',
                                'processEvents',
                                'registerEventListener',
                                'registerSubscriber',
                                'release_allocation',
                                'removeSubscription',
                                'sendEvent',
                                'set_config_parameter',
                                'stage_state',
                                'unregisterEventListener',
                                'unregisterSubscriber',
                                'update_state',
                                'wait_call']

    framework.run()

    # check simulation_log
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        json_lines = json_file.readlines()

    assert len(json_lines) == 3

    event0 = json.loads(json_lines[0])
    event1 = json.loads(json_lines[1])
    event2 = json.loads(json_lines[2])

    assert event0['eventtype'] == 'IPS_START'
    assert event1['eventtype'] == 'IPS_RESOURCE_ALLOC'
    assert event2['eventtype'] == 'IPS_END'

    for event in [event0, event1, event2]:
        assert str(event['ok']) == 'True'
        assert event['sim_name'] == 'test'

    captured = capfd.readouterr()
    assert captured.out.startswith('Starting IPS')
    assert captured.err == ''


def test_framework_empty_config_list(tmpdir):

    with pytest.raises(ValueError) as excinfo:
        Framework(config_file_list=[],
                  log_file_name=str(tmpdir.join('test.log')),
                  platform_file_name='platform.conf',
                  debug=None,
                  verbose_debug=None,
                  cmd_nodes=0,
                  cmd_ppn=0)

    assert str(excinfo.value).endswith("Missing config file? Something is very wrong")

    # check output log file
    with open(str(tmpdir.join('test.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert len(lines) == 3
    assert "FRAMEWORK       ERROR    Missing config file? Something is very wrong\n" in lines
    assert "FRAMEWORK       ERROR    Problem initializing managers\n" in lines
    assert "FRAMEWORK       ERROR    exception encountered while cleaning up config_manager\n" in lines


def test_framework_log_output(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('framework_log_test.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.log("log message")
    framework.debug("debug message")
    framework.info("info message")
    framework.warning("warning message")
    framework.error("error message")
    framework.exception("exception message")
    framework.critical("critical message")

    framework.terminate_all_sims()

    # check output log file
    with open(str(tmpdir.join('framework_log_test.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert len(lines) == 9
    assert "FRAMEWORK       WARNING  warning message\n" in lines
    assert "FRAMEWORK       ERROR    error message\n" in lines
    assert "FRAMEWORK       ERROR    exception message\n" in lines
    assert "FRAMEWORK       CRITICAL critical message\n" in lines

    assert "FRAMEWORK       INFO     log message\n" not in lines
    assert "FRAMEWORK       DEBUG    debug message\n" not in lines
    assert "FRAMEWORK       INFO     info message\n" not in lines


def test_framework_log_output_debug(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('framework_log_debug_test.log')),
                          platform_file_name=str(platform_file),
                          debug=True,
                          verbose_debug=False,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.log("log message")
    framework.debug("debug message")
    framework.info("info message")
    framework.warning("warning message")
    framework.error("error message")
    framework.exception("exception message")
    framework.critical("critical message")

    framework.terminate_all_sims()

    # check output log file
    with open(str(tmpdir.join('framework_log_debug_test.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert len(lines) == 28
    assert "FRAMEWORK       INFO     log message\n" in lines
    assert "FRAMEWORK       DEBUG    debug message\n" in lines
    assert "FRAMEWORK       INFO     info message\n" in lines
    assert "FRAMEWORK       WARNING  warning message\n" in lines
    assert "FRAMEWORK       ERROR    error message\n" in lines
    assert "FRAMEWORK       ERROR    exception message\n" in lines
    assert "FRAMEWORK       CRITICAL critical message\n" in lines


def test_framework_missing_platform(capfd):
    with pytest.raises(SystemExit) as excinfo:
        Framework(config_file_list=[], log_file_name='log')
    assert excinfo.value.code == 1
    captured = capfd.readouterr()
    assert captured.out.endswith('Need to specify a platform file\n')
    assert captured.err == ''
