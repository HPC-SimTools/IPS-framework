from ipsframework.ips import Framework
import glob
import json


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


def test_framework_simple(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(do_create_runspace=True,  # create runspace: init.init()
                          do_run_setup=True,        # validate inputs: sim_comps.init()
                          do_run=True,              # Main part of simulation
                          config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=str(platform_file),
                          compset_list=[],
                          debug=None,
                          ftb=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    assert framework.ips_dosteps['CREATE_RUNSPACE']
    assert framework.ips_dosteps['RUN_SETUP']
    assert framework.ips_dosteps['RUN']

    assert framework.log_file_name.endswith('test.log')

    assert len(framework.config_manager.get_framework_components()) == 2

    component_map = framework.config_manager.get_component_map()

    assert len(component_map)
    assert 'test' in component_map
    test = component_map['test']
    assert len(test) == 1
    assert test[0].get_class_name() == 'test_driver'
    assert test[0].get_instance_name() == 'test@test_driver@1'
    assert test[0].get_seq_num() == 1
    assert test[0].get_serialization() == 'test@test_driver@1'
    assert test[0].get_sim_name() == 'test'

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
