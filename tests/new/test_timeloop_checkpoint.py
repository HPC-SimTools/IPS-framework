from unittest.mock import MagicMock

import pytest

from ipsframework import Framework, ServicesProxy


def write_basic_config_and_platform_files(tmpdir, restart=False):
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

    config_file = tmpdir.join('ips_restart.config') if restart else tmpdir.join('ips.config')

    SIMULATION_MODE = 'RESTART' if restart else 'NORMAL'

    sim_log = 'sim_restart.log' if restart else 'sim.log'

    START = 162.5 if restart else 100
    FINISH = 200 if restart else 150
    NSTEP = 3 if restart else 4

    config = f"""RUN_COMMENT = testing
SIM_NAME = test
LOG_FILE = {tmpdir!s}/{sim_log}
LOG_LEVEL = INFO
SIM_ROOT = {tmpdir!s}
SIMULATION_MODE = {SIMULATION_MODE}
CURRENT_STATE = ${{SIM_NAME}}_ps.dat
STATE_FILES = $CURRENT_STATE
STATE_WORK_DIR = $SIM_ROOT/work/state
RESTART_ROOT = $SIM_ROOT
RESTART_TIME = LATEST
[PORTS]
    NAMES = DRIVER TIMELOOP_COMP TIMELOOP_COMP2
    [[DRIVER]]
      IMPLEMENTATION = TIMELOOP_DRIVER
    [[TIMELOOP_COMP]]
      IMPLEMENTATION = TIMELOOP_COMP
    [[TIMELOOP_COMP2]]
      IMPLEMENTATION = TIMELOOP_COMP2
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
    OUTPUT_FILES = w1_1.dat w1_2.dat
    RESTART_FILES = w1_1.dat $CURRENT_STATE
    SCRIPT =
    MODULE = components.workers.timeloop_comp
[TIMELOOP_COMP2]
    CLASS = TIMELOOP_COMP2
    SUB_CLASS =
    NAME = timeloop_comp
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES = w2_1.dat w2_2.dat
    RESTART_FILES = w2_1.dat $CURRENT_STATE
    SCRIPT =
    MODULE = components.workers.timeloop_comp
[TIME_LOOP]
    MODE = REGULAR
    START = {START}
    FINISH = {FINISH}
    NSTEP = {NSTEP}
[CHECKPOINT]
   MODE = ALL
   NUM_CHECKPOINT = 2
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


def test_timeloop_checkpoint_restart(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(
        config_file_list=[str(config_file)],
        log_file_name=str(tmpdir.join('ips.log')),
        platform_file_name=str(platform_file),
        debug=None,
        verbose_debug=None,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for time in ['100.0', '112.5', '125.0', '137.5', '150.0']:
        assert f'TIMELOOP_COMP__timeloop_comp_2 INFO     step({time})\n' in lines
        assert f'TIMELOOP_COMP2__timeloop_comp_3 INFO     step({time})\n' in lines
        for comp in ['TIMELOOP__timeloop_driver_1', 'TIMELOOP_COMP__timeloop_comp_2', 'TIMELOOP_COMP2__timeloop_comp_3']:
            assert f'{comp} INFO     checkpoint({time})\n' in lines

    # check output files

    # state file
    state_files = tmpdir.join('work').join('state').listdir()
    assert len(state_files) == 1
    state_file = state_files[0].readlines()
    assert len(state_file) == 18

    # restart files
    restart_dir = tmpdir.join('restart')
    assert len(restart_dir.listdir()) == 2
    assert restart_dir.join('137.500').join('TIMELOOP_COMP__timeloop_comp').exists()
    assert restart_dir.join('150.000').join('TIMELOOP_COMP__timeloop_comp').exists()
    assert restart_dir.join('137.500').join('TIMELOOP_COMP2__timeloop_comp').exists()
    assert restart_dir.join('150.000').join('TIMELOOP_COMP2__timeloop_comp').exists()

    # 137.500
    restart_files = restart_dir.join('137.500').join('TIMELOOP_COMP__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w1_1.dat').exists()
    assert len(restart_files.join('w1_1.dat').readlines()) == 5
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 14

    restart_files = restart_dir.join('137.500').join('TIMELOOP_COMP2__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w2_1.dat').exists()
    assert len(restart_files.join('w2_1.dat').readlines()) == 5
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 15

    # 150.000
    restart_files = restart_dir.join('150.000').join('TIMELOOP_COMP__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w1_1.dat').exists()
    assert len(restart_files.join('w1_1.dat').readlines()) == 6
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 17

    restart_files = restart_dir.join('150.000').join('TIMELOOP_COMP2__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w2_1.dat').exists()
    assert len(restart_files.join('w2_1.dat').readlines()) == 6
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 18

    # check output from services.stage_output_files

    results_dir = tmpdir.join('simulation_results')
    assert len(results_dir.listdir()) == 8

    for time in ['100.0', '112.5', '125.0', '137.5', '150.0']:
        assert results_dir.join('TIMELOOP_COMP__timeloop_comp_2').join(f'w1_1_{time}.dat').exists()
        assert results_dir.join('TIMELOOP_COMP__timeloop_comp_2').join(f'w1_2_{time}.dat').exists()
        assert results_dir.join('TIMELOOP_COMP2__timeloop_comp_3').join(f'w2_1_{time}.dat').exists()
        assert results_dir.join('TIMELOOP_COMP2__timeloop_comp_3').join(f'w2_2_{time}.dat').exists()

    # Now do SIMULATION_MODE=RESTART

    platform_file, restart_config_file = write_basic_config_and_platform_files(tmpdir, restart=True)

    framework = Framework(
        config_file_list=[str(restart_config_file)],
        log_file_name=str(tmpdir.join('ips_restart.log')),
        platform_file_name=str(platform_file),
        debug=None,
        verbose_debug=None,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    # check output log file
    with open(str(tmpdir.join('sim_restart.log')), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for time in ['162.5', '175.0', '187.5', '200.0']:
        assert f'TIMELOOP_COMP__timeloop_comp_8 INFO     step({time})\n' in lines
        assert f'TIMELOOP_COMP2__timeloop_comp_9 INFO     step({time})\n' in lines
        for comp in ['TIMELOOP__timeloop_driver_7', 'TIMELOOP_COMP__timeloop_comp_8', 'TIMELOOP_COMP2__timeloop_comp_9']:
            assert f'{comp} INFO     checkpoint({time})\n' in lines

    # check output files

    # state file
    state_files = tmpdir.join('work').join('state').listdir()
    assert len(state_files) == 1
    state_file = state_files[0].readlines()
    assert len(state_file) == 33

    # restart files
    restart_dir = tmpdir.join('restart')
    assert len(restart_dir.listdir()) == 2
    assert restart_dir.join('187.500').join('TIMELOOP_COMP__timeloop_comp').exists()
    assert restart_dir.join('200.000').join('TIMELOOP_COMP__timeloop_comp').exists()
    assert restart_dir.join('187.500').join('TIMELOOP_COMP2__timeloop_comp').exists()
    assert restart_dir.join('200.000').join('TIMELOOP_COMP2__timeloop_comp').exists()

    # 137.500
    restart_files = restart_dir.join('187.500').join('TIMELOOP_COMP__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w1_1.dat').exists()
    assert len(restart_files.join('w1_1.dat').readlines()) == 10
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 29

    restart_files = restart_dir.join('187.500').join('TIMELOOP_COMP2__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w2_1.dat').exists()
    assert len(restart_files.join('w2_1.dat').readlines()) == 10
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 30

    # 200.000
    restart_files = restart_dir.join('200.000').join('TIMELOOP_COMP__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w1_1.dat').exists()
    assert len(restart_files.join('w1_1.dat').readlines()) == 11
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 32

    restart_files = restart_dir.join('200.000').join('TIMELOOP_COMP2__timeloop_comp')
    assert len(restart_files.listdir()) == 2
    assert restart_files.join('w2_1.dat').exists()
    assert len(restart_files.join('w2_1.dat').readlines()) == 11
    assert restart_files.join('test_ps.dat').exists()
    assert len(restart_files.join('test_ps.dat').readlines()) == 33

    # work files, w[1,2]_1.dat should include previous data where w[1,2]_2.dat shouldn't
    work_files = tmpdir.join('work')
    assert work_files.join('TIMELOOP_COMP__timeloop_comp_8').join('w1_1.dat').exists()
    assert work_files.join('TIMELOOP_COMP__timeloop_comp_8').join('w1_2.dat').exists()
    assert work_files.join('TIMELOOP_COMP__timeloop_comp_8').join('test_ps.dat').exists()
    assert len(work_files.join('TIMELOOP_COMP__timeloop_comp_8').join('w1_1.dat').readlines()) == 11
    assert len(work_files.join('TIMELOOP_COMP__timeloop_comp_8').join('w1_2.dat').readlines()) == 5
    assert len(work_files.join('TIMELOOP_COMP__timeloop_comp_8').join('test_ps.dat').readlines()) == 32

    assert work_files.join('TIMELOOP_COMP2__timeloop_comp_9').join('w2_1.dat').exists()
    assert work_files.join('TIMELOOP_COMP2__timeloop_comp_9').join('w2_2.dat').exists()
    assert work_files.join('TIMELOOP_COMP2__timeloop_comp_9').join('test_ps.dat').exists()
    assert len(work_files.join('TIMELOOP_COMP2__timeloop_comp_9').join('w2_1.dat').readlines()) == 11
    assert len(work_files.join('TIMELOOP_COMP2__timeloop_comp_9').join('w2_2.dat').readlines()) == 5
    assert len(work_files.join('TIMELOOP_COMP2__timeloop_comp_9').join('test_ps.dat').readlines()) == 33

    # check output from services.stage_output_files

    results_dir = tmpdir.join('simulation_results')
    assert len(results_dir.listdir()) == 14

    for time in ['162.5', '175.0', '187.5', '200.0']:
        assert results_dir.join('TIMELOOP_COMP__timeloop_comp_8').join(f'w1_1_{time}.dat').exists()
        assert results_dir.join('TIMELOOP_COMP__timeloop_comp_8').join(f'w1_2_{time}.dat').exists()
        assert results_dir.join('TIMELOOP_COMP2__timeloop_comp_9').join(f'w2_1_{time}.dat').exists()
        assert results_dir.join('TIMELOOP_COMP2__timeloop_comp_9').join(f'w2_2_{time}.dat').exists()


def test_TIME_LOOP():
    sim_conf = {'TIME_LOOP': {'MODE': 'REGULAR', 'START': '0', 'FINISH': '10', 'NSTEP': '10'}}
    servicesProxy = ServicesProxy(None, None, None, sim_conf, None)
    tl = servicesProxy.get_time_loop()
    assert tl == list(range(11))

    sim_conf = {'TIME_LOOP': {'MODE': 'REGULAR', 'START': '0 + 20 / 2', 'FINISH': '13 - 1', 'NSTEP': '2'}}
    servicesProxy = ServicesProxy(None, None, None, sim_conf, None)
    tl = servicesProxy.get_time_loop()
    assert tl == [10, 11, 12]

    sim_conf = {'TIME_LOOP': {'MODE': 'REGULAR', 'START': '10 * 2', 'FINISH': '10 ** 2', 'NSTEP': '2'}}
    servicesProxy = ServicesProxy(None, None, None, sim_conf, None)
    tl = servicesProxy.get_time_loop()
    assert tl == [20, 60, 100]

    sim_conf = {'TIME_LOOP': {'MODE': 'REGULAR', 'START': '1e2', 'FINISH': '5e1', 'NSTEP': '2'}}
    servicesProxy = ServicesProxy(None, None, None, sim_conf, None)
    tl = servicesProxy.get_time_loop()
    assert tl == [100, 75, 50]

    sim_conf = {'TIME_LOOP': {'MODE': 'EXPLICIT', 'VALUES': '7 13 -42 1000'}}
    servicesProxy = ServicesProxy(None, None, None, sim_conf, None)
    tl = servicesProxy.get_time_loop()
    assert tl == [7, 13, -42, 1000]

    sim_conf = {'TIME_LOOP': {'MODE': 'REGULAR', 'START': '1p2', 'FINISH': '10', 'NSTEP': '2'}}
    servicesProxy = ServicesProxy(None, None, None, sim_conf, None)
    servicesProxy.error = MagicMock(name='error')
    with pytest.raises(ValueError) as excinfo:
        servicesProxy.get_time_loop()
    assert str(excinfo.value) == 'Invalid TIME_LOOP value of START = 1p2'
