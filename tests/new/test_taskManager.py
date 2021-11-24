import shutil
from unittest import mock
import pytest
from ipsframework import TaskManager, ResourceManager
from ipsframework.messages import ServiceRequestMessage
from ipsframework.ipsExceptions import (BadResourceRequestException,
                                        ResourceRequestMismatchException,
                                        BlockedMessageException,
                                        InsufficientResourcesException,
                                        ResourceRequestUnequalPartitioningException)


def test_build_launch_cmd_fail():

    tm = TaskManager(mock.Mock())

    # test eval
    tm.task_launch_cmd = 'launch_me'
    tm.resource_mgr = mock.Mock(nodes=['node1'])

    with pytest.raises(RuntimeError):
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
    tm.resource_mgr.cores_per_node = 2

    cmd = tm.build_launch_cmd(nproc=4,
                              binary='executable',
                              cmd_args=(),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=True,
                              task_id=None)

    assert cmd == ('srun -N 2 -n 4 executable ', None)

    cmd = tm.build_launch_cmd(nproc=4,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=None,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=True,
                              task_id=None)

    assert cmd == ('srun -N 2 -n 4 executable 13 42', None)

    cmd = tm.build_launch_cmd(nproc=4,
                              binary='executable',
                              cmd_args=(),
                              working_dir=None,
                              ppn=2,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=False,
                              task_id=None,
                              cpp=1)

    assert cmd == ('srun -N 2 -n 4 -c 1 --hint=compute_bound executable ',
                   {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '1'})

    cmd = tm.build_launch_cmd(nproc=2,
                              binary='executable',
                              cmd_args=('13', '42'),
                              working_dir=None,
                              ppn=1,
                              max_ppn=None,
                              nodes='n1,n2',
                              accurateNodes=None,
                              partial_nodes=False,
                              task_id=None,
                              cpp=2)

    assert cmd == ('srun -N 2 -n 2 -c 2 --hint=compute_bound executable 13 42',
                   {'OMP_PLACES': 'threads', 'OMP_PROC_BIND': 'spread', 'OMP_NUM_THREADS': '2'})


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
    rm.initialize(dm, tm, cm,
                  cmd_nodes=2,
                  cmd_ppn=2)

    tm.task_launch_cmd = 'srun'
    rm.accurateNodes = True

    def init_final_task(nproc, tppn, tcpt=0):
        task_id, cmd, _ = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task',
                                                             nproc, 'exe', '/dir', tppn, True,
                                                             True, True, tcpt))
        tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task',
                                             task_id, None))
        return task_id, cmd

    task_id, cmd = init_final_task(1, 0)
    assert task_id == 1
    assert cmd == "srun -N 1 -n 1 -c 2 --hint=compute_bound exe "

    task_id, cmd = init_final_task(2, 0)
    assert task_id == 2
    assert cmd == "srun -N 1 -n 2 -c 1 --hint=compute_bound exe "

    with pytest.raises(ResourceRequestUnequalPartitioningException):
        init_final_task(3, 0)

    task_id, cmd = init_final_task(4, 0)
    assert task_id == 4
    assert cmd == "srun -N 2 -n 4 -c 1 --hint=compute_bound exe "

    with pytest.raises(BadResourceRequestException):
        init_final_task(5, 0)

    task_id, cmd = init_final_task(1, 1)
    assert task_id == 6
    assert cmd == "srun -N 1 -n 1 -c 2 --hint=compute_bound exe "

    task_id, cmd = init_final_task(2, 1)
    assert task_id == 7
    assert cmd == "srun -N 2 -n 2 -c 2 --hint=compute_bound exe "

    with pytest.raises(ResourceRequestMismatchException):
        init_final_task(3, 1)

    fwk.reset_mock()
    task_id, cmd = init_final_task(1, 1, 2)
    assert task_id == 9
    assert cmd == "srun -N 1 -n 1 -c 2 --hint=compute_bound exe "
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd = init_final_task(1, 1, 1)
    assert task_id == 10
    assert cmd == "srun -N 1 -n 1 -c 1 --hint=compute_bound exe "
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd = init_final_task(1, 1, 4)
    assert task_id == 11
    assert cmd == "srun -N 1 -n 1 -c 2 --hint=compute_bound exe "
    fwk.warning.assert_called_once_with("task cpp (4) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead")

    fwk.reset_mock()
    task_id, cmd = init_final_task(2, 1, 2)
    assert task_id == 12
    assert cmd == "srun -N 2 -n 2 -c 2 --hint=compute_bound exe "
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd = init_final_task(2, 1, 1)
    assert task_id == 13
    assert cmd == "srun -N 2 -n 2 -c 1 --hint=compute_bound exe "
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    task_id, cmd = init_final_task(2, 1, 12)
    assert task_id == 14
    assert cmd == "srun -N 2 -n 2 -c 2 --hint=compute_bound exe "
    fwk.warning.assert_called_once_with("task cpp (12) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead")

    # start two task, second should fail with Insufficient Resources depending on block
    task_id, cmd, _ = tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task',
                                                         4, 'exe', '/dir', 0, True,
                                                         True, True, 0))

    with pytest.raises(BlockedMessageException):
        tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task',
                                           1, 'exe', '/dir', 0, True,
                                           True, True, 0))

    with pytest.raises(InsufficientResourcesException):
        tm.init_task(ServiceRequestMessage('id', 'id', 'c', 'init_task',
                                           1, 'exe', '/dir', 0, False,
                                           True, True, 0))


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
    rm.initialize(dm, tm, cm,
                  cmd_nodes=2,
                  cmd_ppn=2)

    tm.task_launch_cmd = 'srun'
    rm.accurateNodes = True

    def init_final_task_pool(nproc=1, tppn=0, number_of_tasks=1, tcpp=0, msg=None):
        if msg is None:
            msg = {f'task{n}': (nproc, '/dir', f'exe{n}', (f'arg{n}',), tppn, True, False, tcpp) for n in range(number_of_tasks)}
        retval = tm.init_task_pool(ServiceRequestMessage('id', 'id', 'c', 'init_task_pool', msg))
        for task_id, _, _ in retval.values():
            tm.finish_task(ServiceRequestMessage('id', 'id', 'c', 'finish_task',
                                                 task_id, None))
        return retval

    retval = init_final_task_pool(1, 0, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 1
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe0 arg0'

    retval = init_final_task_pool(2, 0, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 2
    assert cmd == 'srun -N 1 -n 2 -c 1 --hint=compute_bound exe0 arg0'

    with pytest.raises(ResourceRequestUnequalPartitioningException):
        init_final_task_pool(3, 0, 1)

    retval = init_final_task_pool(4, 0, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 4
    assert cmd == 'srun -N 2 -n 4 -c 1 --hint=compute_bound exe0 arg0'

    with pytest.raises(BadResourceRequestException):
        init_final_task_pool(5, 0, 1)

    retval = init_final_task_pool(1, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 6
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe0 arg0'

    retval = init_final_task_pool(2, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 7
    assert cmd == 'srun -N 2 -n 2 -c 2 --hint=compute_bound exe0 arg0'

    with pytest.raises(ResourceRequestMismatchException):
        init_final_task_pool(3, 1, 1)

    retval = init_final_task_pool(1, 0, 2)
    assert len(retval) == 2
    task_id, cmd, _ = retval['task0']
    assert task_id == 9
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe0 arg0'
    task_id, cmd, _ = retval['task1']
    assert task_id == 10
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe1 arg1'

    retval = init_final_task_pool(2, 0, 2)
    assert len(retval) == 2
    task_id, cmd, _ = retval['task0']
    assert task_id == 11
    assert cmd == 'srun -N 1 -n 2 -c 1 --hint=compute_bound exe0 arg0'
    task_id, cmd, _ = retval['task1']
    assert task_id == 12
    assert cmd == 'srun -N 1 -n 2 -c 1 --hint=compute_bound exe1 arg1'

    retval = init_final_task_pool(4, 0, 2)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 13
    assert cmd == 'srun -N 2 -n 4 -c 1 --hint=compute_bound exe0 arg0'

    # now try with task_cpp set

    fwk.reset_mock()
    retval = init_final_task_pool(1, 1, 1, 2)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 15
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(1, 1, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 16
    assert cmd == 'srun -N 1 -n 1 -c 1 --hint=compute_bound exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(1, 1, 1, 4)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 17
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe0 arg0'
    fwk.warning.assert_called_once_with('task cpp (4) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead')

    fwk.reset_mock()
    retval = init_final_task_pool(2, 1, 1, 2)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 18
    assert cmd == 'srun -N 2 -n 2 -c 2 --hint=compute_bound exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(2, 1, 1, 1)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 19
    assert cmd == 'srun -N 2 -n 2 -c 1 --hint=compute_bound exe0 arg0'
    fwk.warning.assert_not_called()

    fwk.reset_mock()
    retval = init_final_task_pool(2, 1, 1, 4)
    assert len(retval) == 1
    task_id, cmd, _ = retval['task0']
    assert task_id == 20
    assert cmd == 'srun -N 2 -n 2 -c 2 --hint=compute_bound exe0 arg0'
    fwk.warning.assert_called_once_with('task cpp (4) exceeds maximum possible for 1 procs per node with 2 cores per node, using 2 cpus per proc instead')

    # different size tasks
    msg = {'task0': (1, '/dir', 'exe0', ('arg0',), 0, True, False, 0),
           'task1': (2, '/dir', 'exe1', ('arg1',), 0, True, False, 0)}
    retval = init_final_task_pool(msg=msg)
    assert len(retval) == 2
    task_id, cmd, _ = retval['task0']
    assert task_id == 21
    assert cmd == 'srun -N 1 -n 1 -c 2 --hint=compute_bound exe0 arg0'
    task_id, cmd, _ = retval['task1']
    assert task_id == 22
    assert cmd == 'srun -N 1 -n 2 -c 1 --hint=compute_bound exe1 arg1'

    # one good task, one bad task
    msg = {'task0': (1, '/dir', 'exe0', ('arg0',), 0, True, False, 0),
           'task1': (5, '/dir', 'exe1', ('arg1',), 0, True, False, 0)}
    with pytest.raises(BadResourceRequestException):
        init_final_task_pool(msg=msg)

    # one good task, one bad task
    msg = {'task0': (1, '/dir', 'exe0', ('arg0',), 0, True, False, 0),
           'task1': (3, '/dir', 'exe1', ('arg1',), 1, True, False, 0)}
    with pytest.raises(ResourceRequestMismatchException):
        init_final_task_pool(msg=msg)
