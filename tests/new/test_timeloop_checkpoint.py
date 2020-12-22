from ipsframework import Framework


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
LOG_LEVEL = INFO
SIM_ROOT = {str(tmpdir)}
SIMULATION_MODE = NORMAL
[PORTS]
    NAMES = DRIVER TIMELOOP_COMP
    [[DRIVER]]
      IMPLEMENTATION = TIMELOOP_DRIVER
    [[TIMELOOP_COMP]]
      IMPLEMENTATION = TIMELOOP_COMP
[TIMELOOP_DRIVER]
    CLASS = TIMELOOP
    SUB_CLASS =
    NAME = timeloop_driver
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.drivers.timeloop_driver
[TIMELOOP_COMP]
    CLASS = TIMELOOP_COMP
    SUB_CLASS =
    NAME = timeloop_comp
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.workers.timeloop_comp
[TIME_LOOP]
    MODE = REGULAR
    START = 100
    FINISH = 150
    NSTEP = 4
[CHECKPOINT]
   MODE = ALL
   NUM_CHECKPOINT = -1
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_timeloop(tmpdir, capfd):
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

    for time in ["100.0", "112.5", "125.0", "137.5", "150.0"]:
        assert f"TIMELOOP_COMP__timeloop_comp_2 INFO     step({time})\n" in lines
        for comp in ["TIMELOOP__timeloop_driver_1", "TIMELOOP_COMP__timeloop_comp_2"]:
            assert f"{comp} INFO     checkpoint({time})\n" in lines
