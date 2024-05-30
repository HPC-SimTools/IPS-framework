import shutil
from unittest import mock

import pytest

from ipsframework import ResourceManager, TaskManager
from ipsframework.ipsExceptions import (
    BadResourceRequestException,
    BlockedMessageException,
    GPUResourceRequestMismatchException,
    InsufficientResourcesException,
    ResourceRequestMismatchException,
    ResourceRequestUnequalPartitioningException,
)
from ipsframework.messages import ServiceRequestMessage
from ipsframework.taskManager import TaskInit


def test_build_launch_cmd_fail():
    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'launch_me'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    with pytest.raises(RuntimeError):
        tm.build_launch_cmd(
            nproc=1,
            binary='executable',
            cmd_args=(),
            working_dir=None,
            ppn=None,
            max_ppn=None,
            nodes=None,
            accurateNodes=None,
            partial_nodes=None,
            task_id=None,
        )


def test_build_launch_cmd_eval():
    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'eval'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(
        nproc=1, binary='executable', cmd_args=(), working_dir=None, ppn=None, max_ppn=None, nodes=None, accurateNodes=None, partial_nodes=None, task_id=None
    )

    assert cmd == ('executable', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('executable 13 42', None)


@pytest.mark.skipif(not shutil.which('mpirun'), reason='missing mpirun')
def test_build_launch_cmd_mpirun():
    mpirun = shutil.which('mpirun')

    tm = TaskManager(mock.Mock())

    # test mpirun
    tm.task_launch_cmd = 'mpirun'
    tm.resource_mgr = mock.Mock(nodes=['node1'])
    tm.config_mgr = mock.Mock()
    tm.config_mgr.get_platform_parameter.return_value = 'OpenMPI-generic'

    cmd = tm.build_launch_cmd(
        nproc=1, binary='executable', cmd_args=(), working_dir=None, ppn=None, max_ppn=None, nodes=None, accurateNodes=None, partial_nodes=None, task_id=None
    )

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH executable ', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=(),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
        launch_cmd_extra_args='-extra 1',
    )

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH -extra 1 executable ', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=True,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == (f'{mpirun} -np 1 -x PYTHONPATH -H n1,n2 executable 13 42', None)

    # test SGI mpirun
    tm.config_mgr.get_platform_parameter.return_value = 'SGI'
    tm.resource_mgr.cores_per_socket = 4

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=4,
        max_ppn=None,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('mpirun 4 executable 13 42 executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=4,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=True,
        partial_nodes=None,
        task_id=None,
        core_list=[('n1', ['0:1', '3:4']), ('n2', ['0:4'])],
    )

    assert cmd == ('mpirun n1 2 executable 13 42 : n2 1 executable 13 42', {'MPI_DSM_CPULIST': '1,16:4'})


def test_build_launch_cmd_mpiexec():
    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'mpiexec'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(
        nproc=1, binary='executable', cmd_args=(), working_dir=None, ppn=None, max_ppn=None, nodes=None, accurateNodes=None, partial_nodes=None, task_id=None
    )

    assert cmd == ('mpiexec -n 1 executable ', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('mpiexec -n 1 executable 13 42', None)

    tm.resource_mgr = mock.Mock(nodes=['n1', 'n2'])
    tm.host = 'host'

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('mpiexec -n 1 -npernode None executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=True,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('mpiexec --host n1,n2 -n 1 -npernode None executable 13 42', None)


def test_build_launch_cmd_aprun():
    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'aprun'
    tm.resource_mgr = mock.Mock(nodes=['node1'], sockets_per_node=2, cores_per_node=8)
    tm.host = 'not_hopper'

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=4,
        max_ppn=4,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('aprun -n 1 -cc 3-0 -N 4 executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=4,
        max_ppn=4,
        nodes='n1,n2',
        accurateNodes=True,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('aprun -n 1 -N 4 -L n1,n2 executable 13 42', None)

    tm.host = 'hopper'

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=4,
        max_ppn=4,
        nodes=None,
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('aprun -n 1 -N 1 -S 1 executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=4,
        max_ppn=4,
        nodes='n1,n2',
        accurateNodes=True,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('aprun -n 1 -N 1 -S 1 -L n1,n2 executable 13 42', None)


def test_build_launch_cmd_numactl():
    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'numactl'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=None,
        task_id=None,
    )

    assert cmd == ('numactl  executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=True,
        partial_nodes=True,
        task_id=None,
    )

    assert cmd == ('numactl --physcpubind= executable 13 42', None)


def test_build_launch_cmd_srun():
    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'srun'
    tm.resource_mgr = mock.Mock(nodes=['node1'])
    tm.resource_mgr.cores_per_node = 2

    cmd = tm.build_launch_cmd(
        nproc=4, binary='executable', cmd_args=(), working_dir=None, ppn=None, max_ppn=None, nodes='n1,n2', accurateNodes=None, partial_nodes=True, task_id=None
    )

    assert cmd == ('srun -N 2 -n 4 executable ', None)

    cmd = tm.build_launch_cmd(
        nproc=4,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=True,
        task_id=None,
    )

    assert cmd == ('srun -N 2 -n 4 executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=4,
        binary='executable',
        cmd_args=(),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=True,
        task_id=None,
        launch_cmd_extra_args='-extra 1',
    )

    assert cmd == ('srun -N 2 -n 4 -extra 1 executable ', None)

    cmd = tm.build_launch_cmd(
        nproc=4,
        binary='executable',
        cmd_args=(),
        working_dir=None,
        ppn=2,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=False,
        task_id=None,
        cpp=1,
        omp=False,
    )

    assert cmd == ('srun -N 2 -n 4 -c 1 --threads-per-core=1 --cpu-bind=cores executable ', None)

    cmd = tm.build_launch_cmd(
        nproc=2,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=1,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=False,
        task_id=None,
        cpp=2,
        omp=False,
    )

    assert cmd == ('srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=4,
        binary='executable',
        cmd_args=(),
        working_dir=None,
        ppn=2,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=False,
        task_id=None,
        cpp=1,
        omp=True,
    )

    assert cmd == (
        'srun -N 2 -n 4 -c 1 --threads-per-core=1 --cpu-bind=cores executable ',
        {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '1'},
    )

    cmd = tm.build_launch_cmd(
        nproc=2,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=1,
        max_ppn=None,
        nodes='n1,n2',
        accurateNodes=None,
        partial_nodes=False,
        task_id=None,
        cpp=2,
        omp=True,
    )

    assert cmd == (
        'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores executable 13 42',
        {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '2'},
    )

    # now with GPUs

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1',
        accurateNodes=None,
        partial_nodes=False,
        task_id=None,
        cpp=1,
        gpp=1,
        omp=False,
    )

    assert cmd == ('srun -N 1 -n 1 -c 1 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=1 executable 13 42', None)

    cmd = tm.build_launch_cmd(
        nproc=1,
        binary='executable',
        cmd_args=('13', '42'),
        working_dir=None,
        ppn=None,
        max_ppn=None,
        nodes='n1',
        accurateNodes=None,
        partial_nodes=False,
        task_id=None,
        cpp=1,
        gpp=4,
        omp=False,
    )

    assert cmd == ('srun -N 1 -n 1 -c 1 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=4 executable 13 42', None)


def test_init_task_srun(tmpdir):
    # this will combine calls to ResourceManager.get_allocation and
    # TaskManager.build_launch_cmd

    fwk = mock.Mock()
    dm = mock.Mock()
    cm = mock.Mock()
    cm.fwk_sim_name = 'sim_name'
    cm.sim_map = {'sim_name': mock.Mock(sim_root=str(tmpdir))}
    cm.get_platform_parameter.return_value = 'HOST'

    tm = TaskManager(fwk)

    rm = ResourceManager(fwk)

    tm.initialize(dm, rm, cm)
    rm.initialize(dm, tm, cm, cmd_nodes=2, cmd_ppn=2)

    tm.task_launch_cmd = 'srun'
    rm.accurateNodes = True

    def init_final_task(nproc, tppn, tcpt=0):
        task_id, cmd, _, cores_allocated = tm.init_task(
            ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(nproc, 'exe', '/dir', tppn, tcpt, 0, True, True, True, False, [], None))
        )
        tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
        return task_id, cmd, cores_allocated

    task_id, cmd, cores = init_final_task(1, 0)
    assert task_id == 1
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    assert cores == 2

    task_id, cmd, cores = init_final_task(2, 0)
    assert task_id == 2
    assert cmd == 'srun -N 1 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe '
    assert cores == 2

    with pytest.raises(ResourceRequestUnequalPartitioningException):
        init_final_task(3, 0)

    task_id, cmd, cores = init_final_task(4, 0)
    assert task_id == 4
    assert cmd == 'srun -N 2 -n 4 -c 1 --threads-per-core=1 --cpu-bind=cores exe '
    assert cores == 4

    with pytest.raises(BadResourceRequestException):
        init_final_task(5, 0)

    task_id, cmd, cores = init_final_task(1, 1)
    assert task_id == 6
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    assert cores == 2

    task_id, cmd, cores = init_final_task(2, 1)
    assert task_id == 7
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    assert cores == 4

    with pytest.raises(ResourceRequestMismatchException):
        init_final_task(3, 1)

    fwk.reset_mock()
    task_id, cmd, cores = init_final_task(1, 1, 2)
    assert task_id == 9
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd, cores = init_final_task(1, 1, 1)
    assert task_id == 10
    assert cmd == 'srun -N 1 -n 1 -c 1 --threads-per-core=1 --cpu-bind=cores exe '
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd, cores = init_final_task(1, 1, 4)
    assert task_id == 11
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    fwk.warning.assert_called_once_with('task cpp (4) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead')

    fwk.reset_mock()
    task_id, cmd, cores = init_final_task(2, 1, 2)
    assert task_id == 12
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd, cores = init_final_task(2, 1, 1)
    assert task_id == 13
    assert cmd == 'srun -N 2 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe '
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd, cores = init_final_task(2, 1, 12)
    assert task_id == 14
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores exe '
    fwk.warning.assert_called_once_with('task cpp (12) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead')

    (
        task_id,
        cmd,
        _,
        _,
    ) = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(1, 'exe', '/dir', 0, 0, 0, True, True, True, False, [], '-extra 1')))
    tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
    assert task_id == 15
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores -extra 1 exe '

    # start two task, second should fail with Insufficient Resources depending on block
    task_id, cmd, _, _ = tm.init_task(
        ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(4, 'exe', '/dir', 0, 0, 0, True, True, True, False, [], None))
    )

    with pytest.raises(BlockedMessageException):
        tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(1, 'exe', '/dir', 0, 0, 0, True, True, True, False, [], None)))

    with pytest.raises(InsufficientResourcesException):
        tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(1, 'exe', '/dir', 0, 0, 0, False, True, True, False, [], None)))

    tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))

    # request GPUs when there are none
    with pytest.raises(GPUResourceRequestMismatchException) as e:
        tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(1, 'exe', '/dir', 0, 0, 1, False, True, True, False, [], None)))

    assert str(e.value) == 'component id requested 1 processes per node with 1 GPUs per process, which is greater than the available 0 GPUS_PER_NODE'

    # set GPUS_PER_NODE=2
    rm.gpn = 2
    (
        task_id,
        cmd,
        _,
        _,
    ) = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(1, 'exe', '/dir', 0, 0, 1, False, True, True, False, [], None)))
    tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
    assert task_id == 20
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=1 exe '

    (
        task_id,
        cmd,
        _,
        _,
    ) = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(2, 'exe', '/dir', 1, 0, 1, False, True, True, False, [], None)))
    tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
    assert task_id == 21
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=1 exe '

    (
        task_id,
        cmd,
        _,
        _,
    ) = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(2, 'exe', '/dir', 1, 0, 2, False, True, True, False, [], None)))
    tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
    assert task_id == 22
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=2 exe '

    (
        task_id,
        cmd,
        _,
        _,
    ) = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(2, 'exe', '/dir', 2, 0, 1, False, True, True, False, [], None)))
    tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
    assert task_id == 23
    assert cmd == 'srun -N 1 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores --gpus-per-task=1 exe '

    with pytest.raises(GPUResourceRequestMismatchException) as e:
        tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task', TaskInit(2, 'exe', '/dir', 2, 0, 2, False, True, True, False, [], None)))

    assert str(e.value) == 'component id requested 2 processes per node with 2 GPUs per process, which is greater than the available 2 GPUS_PER_NODE'


def test_init_task_pool_srun(tmpdir):
    # this will combine calls to ResourceManager.get_allocation and
    # TaskManager.build_launch_cmd

    fwk = mock.Mock()
    dm = mock.Mock()
    cm = mock.Mock()
    cm.fwk_sim_name = 'sim_name'
    cm.sim_map = {'sim_name': mock.Mock(sim_root=str(tmpdir))}
    cm.get_platform_parameter.return_value = 'HOST'

    tm = TaskManager(fwk)

    rm = ResourceManager(fwk)

    tm.initialize(dm, rm, cm)
    rm.initialize(dm, tm, cm, cmd_nodes=2, cmd_ppn=2)

    tm.task_launch_cmd = 'srun'
    rm.accurateNodes = True

    def init_final_task_pool(nproc=1, tppn=0, number_of_tasks=1, tcpp=0, msg=None):
        if msg is None:
            msg = {f'task{n}': TaskInit(nproc, f'exe{n}', '/dir', tppn, tcpp, 0, False, False, True, False, [f'arg{n}'], None) for n in range(number_of_tasks)}
        retval = tm.init_task_pool(ServiceRequestMessage('id', 'id', 'c', 'init_task_pool', msg))
        for task_id, _, _, _ in retval.values():
            tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task', task_id, None))
        return retval

    retval = init_final_task_pool(1, 0, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 1
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 2

    retval = init_final_task_pool(2, 0, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 2
    assert cmd == 'srun -N 1 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 2

    with pytest.raises(ResourceRequestUnequalPartitioningException):
        init_final_task_pool(3, 0, 1)

    retval = init_final_task_pool(4, 0, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 4
    assert cmd == 'srun -N 2 -n 4 -c 1 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 4

    with pytest.raises(BadResourceRequestException):
        init_final_task_pool(5, 0, 1)

    retval = init_final_task_pool(1, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 6
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 2

    retval = init_final_task_pool(2, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 7
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 4

    with pytest.raises(ResourceRequestMismatchException):
        init_final_task_pool(3, 1, 1)

    retval = init_final_task_pool(1, 0, 2)
    assert len(retval) == 2
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 9
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 2
    task_id, cmd, _, cores = retval['task1']
    assert cores == 2

    retval = init_final_task_pool(2, 0, 2)
    assert len(retval) == 2
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 11
    assert cmd == 'srun -N 1 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 2
    task_id, cmd, _, cores = retval['task1']
    assert task_id == 12
    assert cmd == 'srun -N 1 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe1 arg1'
    assert cores == 2

    retval = init_final_task_pool(4, 0, 2)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 13
    assert cmd == 'srun -N 2 -n 4 -c 1 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 4

    retval = init_final_task_pool(msg={'task0': TaskInit(1, 'exe0', '/dir', 0, 0, 0, False, False, True, False, ('arg0',), '-extra 1')})
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 15
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores -extra 1 exe0 arg0'
    assert cores == 2

    # now try with task_cpp set

    fwk.reset_mock()
    retval = init_final_task_pool(1, 1, 1, 2)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 16
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(1, 1, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 17
    assert cmd == 'srun -N 1 -n 1 -c 1 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(1, 1, 1, 4)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 18
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    fwk.warning.assert_called_once_with('task cpp (4) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead')

    fwk.reset_mock()
    retval = init_final_task_pool(2, 1, 1, 2)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 19
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(2, 1, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 20
    assert cmd == 'srun -N 2 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(2, 1, 1, 4)
    assert len(retval) == 1
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 21
    assert cmd == 'srun -N 2 -n 2 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    fwk.warning.assert_called_once_with('task cpp (4) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead')

    # different size tasks
    msg = {
        'task0': TaskInit(1, 'exe0', '/dir', 0, 0, 0, False, False, True, False, ('arg0',), None),
        'task1': TaskInit(2, 'exe1', '/dir', 0, 0, 0, False, False, True, False, ('arg1',), None),
    }
    retval = init_final_task_pool(msg=msg)
    assert len(retval) == 2
    task_id, cmd, _, cores = retval['task0']
    assert task_id == 22
    assert cmd == 'srun -N 1 -n 1 -c 2 --threads-per-core=1 --cpu-bind=cores exe0 arg0'
    assert cores == 2
    task_id, cmd, _, cores = retval['task1']
    assert task_id == 23
    assert cmd == 'srun -N 1 -n 2 -c 1 --threads-per-core=1 --cpu-bind=cores exe1 arg1'
    assert cores == 2

    # one good task, one bad task
    msg = {
        'task0': TaskInit(1, 'exe0', '/dir', 0, 0, 0, False, False, True, False, ('arg0',), None),
        'task1': TaskInit(5, 'exe1', '/dir', 0, 0, 0, False, False, True, False, ('arg1',), None),
    }
    with pytest.raises(BadResourceRequestException):
        init_final_task_pool(msg=msg)

    # one good task, one bad task
    msg = {
        'task0': TaskInit(1, 'exe0', '/dir', 0, 0, 0, False, False, True, False, ('arg0',), None),
        'task1': TaskInit(3, 'exe1', '/dir', 1, 0, 0, False, False, True, False, ('arg1',), None),
    }
    with pytest.raises(ResourceRequestMismatchException):
        init_final_task_pool(msg=msg)
