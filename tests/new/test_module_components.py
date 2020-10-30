from ipsframework.ips import Framework


def write_basic_config_and_platform_files(tmpdir):
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
    NAMES = DRIVER WORKER
    [[DRIVER]]
      IMPLEMENTATION = HELLO_DRIVER
    [[WORKER]]
      IMPLEMENTATION = HELLO_WORKER
[HELLO_DRIVER]
    CLASS = DRIVERS
    SUB_CLASS = HELLO
    NAME = HelloDriver
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = helloworld.hello_driver
[HELLO_WORKER]
    CLASS = WORKERS
    SUB_CLASS = HELLO
    BIN_PATH =
    NAME = HelloWorker
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = helloworld.hello_worker
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_using_module_components(tmpdir, capfd):
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
    assert test[0].get_class_name() == 'HelloDriver'
    assert test[0].get_instance_name().startswith('test@HelloDriver')
    assert test[0].get_serialization().startswith('test@HelloDriver')
    assert test[0].get_sim_name() == 'test'

    # Don't run anything, just check initialization of components
    framework.terminate_all_sims()

    captured = capfd.readouterr()

    captured_out = captured.out.split('\n')
    assert captured_out[0] == "Created <class 'helloworld.hello_driver.HelloDriver'>"
    assert captured_out[1] == "Created <class 'helloworld.hello_worker.HelloWorker'>"
    assert captured.err == ''
