import glob
import json

import pytest

from ipsframework import Framework


def write_basic_config_and_platform_files(tmpdir):
    platform_file = tmpdir.join('perlmutter.platform.conf')

    platform = """MPIRUN = srun
HOST = perlmutter
NODE_DETECTION = slurm_env
CORES_PER_NODE = 64
PROCS_PER_NODE = 64
GPUS_PER_NODE = 4
SOCKETS_PER_NODE = 1
NODE_ALLOCATION_MODE = EXCLUSIVE
USE_ACCURATE_NODES = ON
"""

    with open(platform_file, 'w') as f:
        f.write(platform)

    config_file = tmpdir.join('ips.config')

    config = f"""RUN_COMMENT = testing
SIM_NAME = test
LOG_FILE = {tmpdir!s}/sim.log
LOG_LEVEL = INFO
SIM_ROOT = {tmpdir!s}
SIMULATION_MODE = NORMAL
[PORTS]
    NAMES = DRIVER
    [[DRIVER]]
      IMPLEMENTATION = DRIVER
[DRIVER]
    CLASS = OPENMP
    SUB_CLASS =
    NAME = gpu_task
    BIN_PATH =
    EXE = {tmpdir!s}/gpu_test.sh
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.workers.perlmutter_srun_gpu
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


@pytest.mark.perlmutter
def test_srun_gpu_on_perlmutter(tmpdir):
    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    exe = tmpdir.join('gpu_test.sh')
    exe.write('#!/bin/bash\nmkdir -p $1\nnvidia-smi -L > $1/proc_${SLURM_PROCID}_GPUS.log\n')
    exe.chmod(448)  # 700

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

    # check simulation_log
    json_files = glob.glob(str(tmpdir.join('simulation_log').join('*.json')))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        comments = [json.loads(line)['comment'].split(', ', maxsplit=4)[3:] for line in json_file.readlines()]

    assert comments[5][0].startswith('Target = srun -N 1 -n 1 -c 64 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=1')
    assert comments[5][0].endswith('gpu_test.sh 1_1')

    assert comments[7][0].startswith('Target = srun -N 1 -n 1 -c 64 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=2')
    assert comments[7][0].endswith('gpu_test.sh 1_2')

    assert comments[9][0].startswith('Target = srun -N 1 -n 1 -c 64 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=4')
    assert comments[9][0].endswith('gpu_test.sh 1_4')

    assert comments[11][0].startswith('Target = srun -N 1 -n 2 -c 32 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=2')
    assert comments[11][0].endswith('gpu_test.sh 2_2')

    assert comments[13][0].startswith('Target = srun -N 1 -n 4 -c 16 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=1')
    assert comments[13][0].endswith('gpu_test.sh 4_1')

    # check that the process output log files are created
    work_dir = tmpdir.join('work').join('OPENMP__gpu_task_1')

    for nprocs, ngpus in ((1, 1), (1, 2), (1, 4), (2, 2), (4, 1)):
        output_files = glob.glob(str(work_dir.join(f'{nprocs}_{ngpus}').join('*.log')))
        assert len(output_files) == nprocs
        for n in range(nprocs):
            lines = open(output_files[n], 'r').readlines()
            assert len(lines) == ngpus
