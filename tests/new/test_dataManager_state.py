from ipsframework import Framework
import os


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
LOG_FILE = {str(tmpdir)}/sim.log
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
CURRENT_STATE = state.dat
STATE_FILES = $CURRENT_STATE state100.dat
STATE_WORK_DIR = $SIM_ROOT/work/state

[PORTS]
    NAMES = INIT DRIVER
    [[INIT]]
      IMPLEMENTATION = init
    [[DRIVER]]
      IMPLEMENTATION = driver
[init]
    CLASS = DATA_INIT
    SUB_CLASS =
    NAME = init_dataManager
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.drivers.init_dataManager
[driver]
    CLASS = DATA_DRIVER
    SUB_CLASS =
    NAME = driver_dataManager
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.drivers.driver_dataManager
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_dataManager_state_file(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check output files exist
    for filename in ['state.dat', 'state100.dat']:
        assert os.path.exists(str(tmpdir.join('work').join('DATA_INIT__init_dataManager_1').join(filename)))
        assert os.path.exists(str(tmpdir.join('work').join('DATA_DRIVER__driver_dataManager_2').join(filename)))
        assert os.path.exists(str(tmpdir.join('work').join('state').join(filename)))

    # check output log file
    test_map = (('DATA_INIT__init_dataManager_1', 'state.dat', 1),
                ('DATA_INIT__init_dataManager_1', 'state100.dat', 100),
                ('DATA_DRIVER__driver_dataManager_2', 'state.dat', 2),
                ('DATA_DRIVER__driver_dataManager_2', 'state100.dat', 101),
                ('state', 'state.dat', 2),
                ('state', 'state100.dat', 101))
    for (direc, filename, result) in test_map:
        with open(str(tmpdir.join('work').join(direc).join(filename)), 'r') as f:
            value = int(f.readline())
        assert value == result

    # check merge_current_state logfile
    logfile = str(tmpdir.join('work').join('DATA_DRIVER__driver_dataManager_2').join('merge_current_state.log'))
    assert os.path.exists(logfile)
    # remove tmpdir from log output
    log = open(logfile).readline().replace(str(tmpdir), '')
    assert log == '-input /work/state/state.dat -updates /work/DATA_DRIVER__driver_dataManager_2/partial_state_file\n'
