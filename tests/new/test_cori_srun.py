import glob
import json
import pytest
from ipsframework import Framework


def write_basic_config_and_platform_files(tmpdir):
    platform_file = tmpdir.join('cori.platform.conf')

    platform = """MPIRUN = srun
HOST = cori
NODE_DETECTION = slurm_env
CORES_PER_NODE = 32
SOCKETS_PER_NODE = 2
NODE_ALLOCATION_MODE = exclusive
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
    NAMES = DRIVER
    [[DRIVER]]
      IMPLEMENTATION = DRIVER
[DRIVER]
    CLASS = OPENMP
    SUB_CLASS =
    NAME = openmp_worker
    BIN_PATH =
    NPROC = 1
    INPUT_FILES =
    OUTPUT_FILES =
    SCRIPT =
    MODULE = components.workers.cori_srun_openmp
"""

    with open(config_file, 'w') as f:
        f.write(config)

    return platform_file, config_file


@pytest.mark.cori
def test_srun_openmp_on_cori(tmpdir):

    platform_file, config_file = write_basic_config_and_platform_files(tmpdir)

    framework = Framework(config_file_list=[str(config_file)],
                          log_file_name=str(tmpdir.join('ips.log')),
                          platform_file_name=str(platform_file),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # check simulation_log
    json_files = glob.glob(str(tmpdir.join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        comments = [json.loads(line)['comment'].split(', ', maxsplit=4)[3:] for line in json_file.readlines()]

    # check that the process output log files are created
    work_dir = tmpdir.join("work").join("OPENMP__openmp_worker_1")

    # 0
    for c in (2, 4, 6):
        assert comments[c][0] == "Target = srun -N 1 -n 1 -c 32 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-mpi.gnu.cori "
        assert comments[c][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '32'}"

    for log in ('01', '02', '03'):
        lines = sorted(work_dir.join(f"log.{log}").readlines())
        assert lines[0].startswith('Hello from rank 0') and lines[0].endswith('(core affinity = 0-63)\n')

    # 1
    for c in (8, 10, 12):
        assert comments[c][0] == "Target = srun -N 1 -n 4 -c 8 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-mpi.gnu.cori "
        assert comments[c][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '8'}"

    for log in ('11', '12', '13'):
        lines = sorted(work_dir.join(f"log.{log}").readlines())
        assert lines[0].startswith('Hello from rank 0') and lines[0].endswith('(core affinity = 0-7,32-39)\n')
        assert lines[1].startswith('Hello from rank 1') and lines[1].endswith('(core affinity = 16-23,48-55)\n')
        assert lines[2].startswith('Hello from rank 2') and lines[2].endswith('(core affinity = 8-15,40-47)\n')
        assert lines[3].startswith('Hello from rank 3') and lines[3].endswith('(core affinity = 24-31,56-63)\n')

    # 2
    for c in (14, 16, 18):
        assert comments[c][0] == "Target = srun -N 1 -n 32 -c 1 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-mpi.gnu.cori "
        assert comments[c][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '1'}"

    for log in ('21', '22', '23'):
        lines = sorted(work_dir.join(f"log.{log}").readlines(), key=lambda a: int(a.split()[3].replace(',', '')))
        for n, l in enumerate(lines):
            cores = n//2 + n % 2*16
            assert lines[n].startswith(f'Hello from rank {n}') and lines[n].endswith(f'(core affinity = {cores},{cores+32})\n')

    # 31
    assert comments[20][0] == "Target = srun -N 1 -n 4 -c 8 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-mpi.gnu.cori "
    assert comments[20][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '8'}"

    lines = sorted(work_dir.join("log.31").readlines())
    assert lines[0].startswith('Hello from rank 0') and lines[0].endswith('(core affinity = 0-7,32-39)\n')
    assert lines[1].startswith('Hello from rank 1') and lines[1].endswith('(core affinity = 16-23,48-55)\n')
    assert lines[2].startswith('Hello from rank 2') and lines[2].endswith('(core affinity = 8-15,40-47)\n')
    assert lines[3].startswith('Hello from rank 3') and lines[3].endswith('(core affinity = 24-31,56-63)\n')

    # 32
    assert comments[22][0] == "Target = srun -N 1 -n 4 -c 4 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-mpi.gnu.cori "
    assert comments[22][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '4'}"

    lines = sorted(work_dir.join("log.32").readlines())
    assert lines[0].startswith('Hello from rank 0') and lines[0].endswith('(core affinity = 0,1,32,33)\n')
    assert lines[1].startswith('Hello from rank 1') and lines[1].endswith('(core affinity = 16,17,48,49)\n')
    assert lines[2].startswith('Hello from rank 2') and lines[2].endswith('(core affinity = 2,3,34,35)\n')
    assert lines[3].startswith('Hello from rank 3') and lines[3].endswith('(core affinity = 18,19,50,51)\n')

    # 33
    assert comments[24][0] == "Target = srun -N 1 -n 4 -c 2 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-mpi.gnu.cori "
    assert comments[24][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '2'}"

    lines = sorted(work_dir.join("log.33").readlines())
    assert lines[0].startswith('Hello from rank 0') and lines[0].endswith('(core affinity = 0-3,32-35)\n')
    assert lines[1].startswith('Hello from rank 1') and lines[1].endswith('(core affinity = 16-19,48-51)\n')
    assert lines[2].startswith('Hello from rank 2') and lines[2].endswith('(core affinity = 4-7,36-39)\n')
    assert lines[3].startswith('Hello from rank 3') and lines[3].endswith('(core affinity = 20-23,52-55)\n')

    # openmp

    # 41
    assert comments[26][0] == "Target = srun -N 1 -n 4 -c 8 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-hybrid.gnu.cori "
    assert comments[26][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '8'}"

    lines = sorted(work_dir.join("log.41").readlines())
    for n, l in enumerate(lines):
        assert l.startswith(f"Hello from rank {n//8}, thread {n%8}")
        assert l.endswith(f"(core affinity = {n%8 + n//16*8 + n//8%2*16})\n")

    # 42
    assert comments[28][0] == "Target = srun -N 1 -n 4 -c 4 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-hybrid.gnu.cori "
    assert comments[28][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '4'}"

    lines = sorted(work_dir.join("log.42").readlines())
    for n, l in enumerate(lines):
        assert l.startswith(f"Hello from rank {n//4}, thread {n%4}")
        assert l.endswith(f"(core affinity = {n%4 + n//8*4 + n//4%2*16})\n")

    # 43
    assert comments[30][0] == "Target = srun -N 1 -n 4 -c 2 --threads-per-core=1 --cpu-bind=cores /usr/common/software/bin/check-hybrid.gnu.cori "
    assert comments[30][1] == "env = {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '2'}"

    lines = sorted(work_dir.join("log.43").readlines())
    for n, l in enumerate(lines):
        assert l.startswith(f"Hello from rank {n//2}, thread {n%2}")
        assert l.endswith(f"(core affinity = {n%2 + n//4*2 + n//2%2*16})\n")
