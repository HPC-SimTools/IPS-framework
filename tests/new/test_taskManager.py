from ipsframework.taskManager import TaskManager
import pytest
import shutil
from unittest import mock


def test_build_launch_cmd_fail():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'launch_me'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    with pytest.raises(TypeError):
        tm.build_launch_cmd(nproc=1,
                            binary='executable',
                            cmd_args=(),
                            working_dir=None,
                            ppn=None,
                            max_ppn=None,
                            nodes=None,
                            accurateNodes=None,
                            partial_nodes=None,
                            task_id=None)


def test_build_launch_cmd_eval():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'eval'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=(),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('executable', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('executable 13 42', None)


@pytest.mark.skipif(not shutil.which('mpirun'), reason="missing mpirun")
def test_build_launch_cmd_mpirun():

    mpirun = shutil.which('mpirun')

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'mpirun'
    tm.resource_mgr = mock.Mock(nodes=['node1'])
    tm.config_mgr = mock.Mock()
    tm.config_mgr.get_platform_parameter.return_value = 'OpenMPI-generic'

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=(),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH executable ', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=True,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH -H n1,n2 executable 13 42', None)

    # test SGI mpirun
    tm.config_mgr.get_platform_parameter.return_value = 'SGI'
    tm.resource_mgr.cores_per_socket = 4

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=4,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('mpirun 4 executable 13 42 executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=4,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=True,
                              partial_nodes=None,
                              task_id=None,
                              core_list=[('n1', ['0:1', '3:4']), ('n2', ['0:4'])])

    assert cmd == ('mpirun n1 2 executable 13 42 : n2 1 executable 13 42', {'MPI_DSM_CPULIST': '1,16:4'})


def test_build_launch_cmd_mpiexec():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'mpiexec'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=(),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('mpiexec -n 1 executable ', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('mpiexec -n 1 executable 13 42', None)

    tm.resource_mgr = mock.Mock(nodes=['n1', 'n2'])
    tm.host = 'host'

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('mpiexec -n 1 -npernode None executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=True,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('mpiexec --host n1,n2 -n 1 -npernode None executable 13 42', None)


def test_build_launch_cmd_aprun():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'aprun'
    tm.resource_mgr = mock.Mock(nodes=['node1'], sockets_per_node=2, cores_per_node=8)
    tm.host = 'not_hopper'

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=4,
                              max_ppn=4,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('aprun -n 1 -cc 3-0 -N 4 executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=4,
                              max_ppn=4,
                              nodes='n1,n2',
                              accurateNodes=True,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('aprun -n 1 -N 4 -L n1,n2 executable 13 42', None)

    tm.host = 'hopper'

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=4,
                              max_ppn=4,
                              nodes=None,
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('aprun -n 1 -N 1 -S 1 executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=4,
                              max_ppn=4,
                              nodes='n1,n2',
                              accurateNodes=True,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('aprun -n 1 -N 1 -S 1 -L n1,n2 executable 13 42', None)


def test_build_launch_cmd_numactl():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'numactl'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('numactl  executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=True,
                              partial_nodes=True,
                              task_id=None)

    assert cmd == ('numactl --physcpubind= executable 13 42', None)


def test_build_launch_cmd_srun():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'srun'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=(),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('srun -N 2 -n 1 executable ', None)

    cmd = tm.build_launch_cmd(nproc=1,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=None,
                              task_id=None)

    assert cmd == ('srun -N 2 -n 1 executable 13 42', None)
