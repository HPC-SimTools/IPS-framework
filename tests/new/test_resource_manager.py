import io
from unittest import mock

import pytest

from ipsframework.ips_exceptions import (
    BadResourceRequestError,
    GpuResourceRequestMismatchError,
    InsufficientResourcesError,
    ResourceRequestMismatchError,
    ResourceRequestUnequalPartitioningError,
)
from ipsframework.resource_manager import ResourceManager


def test_allocations(tmpdir):
    fwk = mock.Mock()
    dm = mock.Mock()
    tm = mock.Mock()
    cm = mock.Mock()
    cm.fwk_sim_name = 'sim_name'
    cm.sim_map = {'sim_name': mock.Mock(sim_root=str(tmpdir))}
    cm.get_platform_parameter.return_value = 'HOST'

    rm = ResourceManager(fwk)
    rm.initialize(dm, tm, cm, cmd_nodes=2, cmd_ppn=4)

    for node in ('dummy_node0', 'dummy_node1'):
        with io.StringIO() as output:
            rm.nodes[node].print_sockets(output)
            lines = [s.strip() for s in output.getvalue().split('\n')]
            assert lines[0] == 'socket: 0'
            assert lines[1] == 'availablilty: 4'
            assert lines[2] == 'task ids: []'
            assert lines[3] == 'owners: []'
            assert lines[4] == 'cores: 4'
            assert lines[5] == 'core: 0  - available'
            assert lines[6] == 'core: 1  - available'
            assert lines[7] == 'core: 2  - available'
            assert lines[8] == 'core: 3  - available'

    assert rm.check_whole_node_cap(1, 1) == (True, ['dummy_node0'])
    assert rm.check_whole_node_cap(2, 1) == (True, ['dummy_node0', 'dummy_node1'])
    assert rm.check_whole_node_cap(1, 2) == (True, ['dummy_node0'])
    assert rm.check_whole_node_cap(3, 1) == (False, 'mismatch')
    assert rm.check_whole_node_cap(1, 16) == (False, 'insufficient')

    assert rm.check_whole_sock_cap(1, 1) == (True, ['dummy_node0'])
    assert rm.check_whole_sock_cap(2, 1) == (True, ['dummy_node0', 'dummy_node1'])
    assert rm.check_whole_sock_cap(1, 2) == (True, ['dummy_node0'])
    assert rm.check_whole_sock_cap(3, 1) == (False, 'mismatch')

    assert rm.check_core_cap(1, 1) == (True, ['dummy_node0'])
    assert rm.check_core_cap(2, 1) == (True, ['dummy_node0', 'dummy_node1'])
    assert rm.check_core_cap(1, 2) == (True, ['dummy_node0'])
    assert rm.check_core_cap(3, 1) == (False, 'mismatch')

    # I think the following should return insufficient but it doesn't?
    # assert rm.check_whole_node_cap(4, 4) == (False, 'insufficient')
    # assert rm.check_whole_sock_cap(1, 16) == (False, 'insufficient')
    # assert rm.check_whole_sock_cap(4, 4) == (False, 'insufficient')
    # assert rm.check_core_cap(1, 16) == (False, 'insufficient')
    # assert rm.check_core_cap(4, 4) == (False, 'insufficient')

    with pytest.raises(BadResourceRequestError) as excinfo:
        rm.get_allocation(comp_id='comp0', nproc=12, task_id=0, whole_nodes=True, whole_socks=False)

    assert (
        str(excinfo.value)
        == 'component comp0 requested 3 nodes, which is more than possible by 1 nodes, for task 0.'
    )

    with pytest.raises(ResourceRequestUnequalPartitioningError) as excinfo:
        rm.get_allocation(
            comp_id='comp0', nproc=3, task_id=0, whole_nodes=True, whole_socks=False, task_ppn=2
        )

    assert (
        str(excinfo.value)
        == 'component comp0 requested 3 processes with 2 processes per node, while the number of processes requested is '
        'less than the max (8), it will result in unequal partitioning of processes across nodes'
    )

    with pytest.raises(BadResourceRequestError) as excinfo:
        rm.get_allocation(comp_id='comp0', nproc=12, task_id=0, whole_nodes=False, whole_socks=True)

    assert (
        str(excinfo.value)
        == 'component comp0 requested 3 nodes, which is more than possible by 1 nodes, for task 0.'
    )

    with pytest.raises(ResourceRequestMismatchError) as excinfo:
        rm.get_allocation(
            comp_id='comp0', nproc=6, task_id=0, whole_nodes=False, whole_socks=False, task_ppn=2
        )

    assert (
        str(excinfo.value)
        == 'component comp0 requested 6 processes with 2 processes per node, while the number of processes requested is '
        'less than the max (8), the processes per node value is too low.'
    )

    rm.get_allocation(comp_id='comp0', nproc=2, task_id=0, whole_nodes=False, whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 2'
        assert lines[2] == 'task ids: [0]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 0  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 0  - owner: comp0'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 4'
        assert lines[2] == 'task ids: []'
        assert lines[3] == 'owners: []'
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    rm.get_allocation(comp_id='comp0', nproc=2, task_id=1, whole_nodes=True, whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 2'
        assert lines[2] == 'task ids: [0]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 0  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 0  - owner: comp0'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [1]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 1  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 1  - owner: comp0'
        assert lines[7] == 'core: 2  - task_id: 1  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 1  - owner: comp0'

    rm.get_allocation(comp_id='comp0', nproc=2, task_id=2, whole_nodes=False, whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [0, 2]'
        assert lines[3] == "owners: ['comp0', 'comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 0  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 0  - owner: comp0'
        assert lines[7] == 'core: 2  - task_id: 2  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 2  - owner: comp0'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [1]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 1  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 1  - owner: comp0'
        assert lines[7] == 'core: 2  - task_id: 1  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 1  - owner: comp0'

    with pytest.raises(InsufficientResourcesError) as excinfo:
        rm.get_allocation(comp_id='comp0', nproc=1, task_id=3, whole_nodes=False, whole_socks=False)

    assert (
        str(excinfo.value)
        == 'component comp0 requested 1 nodes, which is more than available by 0 nodes, for task 3.'
    )

    rm.release_allocation(task_id=1, status=None)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [0, 2]'
        assert lines[3] == "owners: ['comp0', 'comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 0  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 0  - owner: comp0'
        assert lines[7] == 'core: 2  - task_id: 2  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 2  - owner: comp0'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 4'
        assert lines[2] == 'task ids: []'
        assert lines[3] == 'owners: []'
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    rm.release_allocation(task_id=0, status=None)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 2'
        assert lines[2] == 'task ids: [2]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - task_id: 2  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 2  - owner: comp0'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 4'
        assert lines[2] == 'task ids: []'
        assert lines[3] == 'owners: []'
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    rm.release_allocation(task_id=2, status=None)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 4'
        assert lines[2] == 'task ids: []'
        assert lines[3] == 'owners: []'
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 4'
        assert lines[2] == 'task ids: []'
        assert lines[3] == 'owners: []'
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    rm.get_allocation(comp_id='comp1', nproc=2, task_id=9, whole_nodes=False, whole_socks=True)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [9]'
        assert lines[3] == "owners: ['comp1']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 9  - owner: comp1'
        assert lines[6] == 'core: 1  - task_id: 9  - owner: comp1'
        assert lines[7] == 'core: 2  - task_id: 9  - owner: comp1'
        assert lines[8] == 'core: 3  - task_id: 9  - owner: comp1'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 4'
        assert lines[2] == 'task ids: []'
        assert lines[3] == 'owners: []'
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - available'
        assert lines[6] == 'core: 1  - available'
        assert lines[7] == 'core: 2  - available'
        assert lines[8] == 'core: 3  - available'

    # test GPUs
    with pytest.raises(GpuResourceRequestMismatchError) as excinfo:
        rm.get_allocation(
            comp_id='comp0', nproc=1, task_gpp=1, task_id=0, whole_nodes=True, whole_socks=False
        )

    assert (
        str(excinfo.value)
        == 'component comp0 requested 1 processes per node with 1 GPUs per process, which is greater than the available 0 GPUS_PER_NODE'
    )

    # set GPUS_PER_NODE to 2
    rm = ResourceManager(fwk)
    rm.initialize(dm, tm, cm, cmd_nodes=2, cmd_ppn=4)
    rm.gpn = 2

    with pytest.raises(GpuResourceRequestMismatchError) as excinfo:
        rm.get_allocation(
            comp_id='comp0', nproc=1, task_gpp=4, task_id=0, whole_nodes=True, whole_socks=False
        )

    assert (
        str(excinfo.value)
        == 'component comp0 requested 1 processes per node with 4 GPUs per process, which is greater than the available 2 GPUS_PER_NODE'
    )

    with pytest.raises(GpuResourceRequestMismatchError) as excinfo:
        rm.get_allocation(
            comp_id='comp0', nproc=2, task_gpp=2, task_id=0, whole_nodes=True, whole_socks=False
        )

    assert (
        str(excinfo.value)
        == 'component comp0 requested 2 processes per node with 2 GPUs per process, which is greater than the available 2 GPUS_PER_NODE'
    )

    rm.get_allocation(
        comp_id='comp0',
        nproc=2,
        task_ppn=1,
        task_gpp=2,
        task_id=0,
        whole_nodes=True,
        whole_socks=False,
    )

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [0]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 0  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 0  - owner: comp0'
        assert lines[7] == 'core: 2  - task_id: 0  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 0  - owner: comp0'

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == 'socket: 0'
        assert lines[1] == 'availablilty: 0'
        assert lines[2] == 'task ids: [0]'
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == 'cores: 4'
        assert lines[5] == 'core: 0  - task_id: 0  - owner: comp0'
        assert lines[6] == 'core: 1  - task_id: 0  - owner: comp0'
        assert lines[7] == 'core: 2  - task_id: 0  - owner: comp0'
        assert lines[8] == 'core: 3  - task_id: 0  - owner: comp0'


@pytest.mark.parametrize('cpp', [2, 4])
def test_dvm_complete_ranks(tmp_path, cpp: int) -> None:
    """Ensure ranks cannot be split across nodes with fragmented capacity.

    :param tmp_path: Isolated resource report directory.
    :param cpp: Physical cores per MPI rank.
    :returns: None.
    """
    cm = mock.Mock()
    cm.fwk_sim_name = 'test'
    cm.sim_map = {'test': mock.Mock(sim_root=str(tmp_path))}
    cm.get_platform_parameter.return_value = 'HOST'
    rm = ResourceManager(mock.Mock())
    rm.initialize(mock.Mock(), mock.Mock(), cm, cmd_nodes=2, cmd_ppn=4)
    cm.get_platform_parameter.return_value = 'OPENMPI-DVM'
    # One rank on each node leaves fewer than cpp free cores on each.
    rm.get_allocation('first', 2, 1, False, False, task_ppn=1, task_cpp=3)
    with pytest.raises(InsufficientResourcesError):
        rm.get_allocation('second', 1, 2, False, False, task_cpp=cpp)
    assert rm.avail_cores == 2
    assert rm.processes == 2
    rm.release_allocation(1, 0)
    result = rm.get_allocation('second', 2, 3, False, False, task_cpp=cpp)
    assert result.cores_allocated == 2 * cpp
    assert result.ppn == min(2, 4 // cpp)
    rm.release_allocation(3, 0)
    assert rm.avail_cores == 8
    for invalid in (-1, 1.5, '4'):
        with pytest.raises(ValueError):
            rm.get_allocation('invalid', 1, 4, False, False, task_cpp=invalid)
    rm.reporting_file.close()


@pytest.mark.parametrize(
    'whole_nodes,whole_socks,reserved', [(False, False, 4), (False, True, 4), (True, True, 8)]
)
def test_dvm_unequal_core_and_rank_limits(
    tmp_path, whole_nodes: bool, whole_socks: bool, reserved: int
) -> None:
    """Initialize from an eight-core, two-rank platform and verify allocation.

    :param tmp_path: Resource-report directory.
    :param whole_nodes: Reserve complete nodes.
    :param whole_socks: Reserve complete sockets.
    :param reserved: Expected CPU reservation.
    :returns: None.
    """
    params = {
        'HOST': 'test',
        'MPIRUN_VERSION': 'OPENMPI-DVM',
        'NODE_DETECTION': 'manual',
        'CORES_PER_NODE': 8,
        'PROCS_PER_NODE': 2,
        'NODES': 1,
        'TOTAL_PROCS': 0,
        'SOCKETS_PER_NODE': 2,
        'NODE_ALLOCATION_MODE': 'SHARED',
        'GPUS_PER_NODE': 0,
    }
    cm = mock.Mock()
    cm.fwk_sim_name = 'test'
    cm.sim_map = {'test': mock.Mock(sim_root=str(tmp_path))}
    cm.get_platform_parameter.side_effect = lambda key, **kwargs: params.get(key)
    rm = ResourceManager(mock.Mock())
    rm.initialize(mock.Mock(), mock.Mock(), cm)
    assert rm.total_cores == rm.avail_cores == 8
    assert rm.ppn == rm.max_ppn == 2
    result = rm.get_allocation('test', 1, 1, whole_nodes, whole_socks, task_cpp=4)
    assert result.cores_allocated == reserved
    assert result.ppn == 1
    assert rm.processes == 1
    rm.release_allocation(1, 0)
    assert rm.avail_cores == 8
    result = rm.get_allocation('test', 2, 2, False, False, task_cpp=4)
    assert result.cores_allocated == 8
    assert result.ppn == 2
    with pytest.raises(InsufficientResourcesError):
        rm.get_allocation('blocked', 1, 3, False, False, task_cpp=1)
    assert rm.avail_cores == 0
    rm.release_allocation(2, 0)
    with pytest.raises(BadResourceRequestError):
        rm.get_allocation('oversized', 2, 4, False, False, task_cpp=5)
    assert rm.avail_cores == 8
    assert rm.processes == rm.alloc_cores == 0
    # Separate tasks may each launch one rank while sharing the CPU budget.
    rm.get_allocation('first', 1, 5, False, False, task_cpp=4)
    rm.get_allocation('second', 1, 6, False, False, task_cpp=4)
    assert rm.alloc_cores == 8
    rm.release_allocation(5, 0)
    rm.release_allocation(6, 0)
    assert rm.avail_cores == 8
    rm.reporting_file.close()


def test_dvm_rank_limit_does_not_destroy_cpu_capacity(tmp_path) -> None:
    """Track concurrent rank occupancy independently from reserved CPUs.

    :param tmp_path: Resource-report directory.
    :returns: None.
    """
    params = {
        'HOST': 'test',
        'MPIRUN_VERSION': 'OPENMPI-DVM',
        'NODE_DETECTION': 'manual',
        'CORES_PER_NODE': 8,
        'PROCS_PER_NODE': 2,
        'NODES': 1,
        'TOTAL_PROCS': 0,
        'SOCKETS_PER_NODE': 1,
        'NODE_ALLOCATION_MODE': 'SHARED',
        'GPUS_PER_NODE': 0,
    }
    cm = mock.Mock()
    cm.fwk_sim_name = 'test'
    cm.sim_map = {'test': mock.Mock(sim_root=str(tmp_path))}
    cm.get_platform_parameter.side_effect = lambda key, **kwargs: params.get(key)
    rm = ResourceManager(mock.Mock())
    rm.initialize(mock.Mock(), mock.Mock(), cm)
    rm.get_allocation('first', 1, 1, False, False, task_cpp=1)
    rm.get_allocation('second', 1, 2, False, False, task_cpp=1)
    assert rm.avail_cores == 6
    with pytest.raises(InsufficientResourcesError):
        rm.get_allocation('third', 1, 3, False, False, task_cpp=1)
    rm.release_allocation(1, 0)
    allocation = rm.get_allocation('third', 1, 3, False, False, task_cpp=4)
    assert allocation.cores_allocated == 4
    assert rm.avail_cores == 3
    rm.release_allocation(2, 0)
    rm.release_allocation(3, 0)
    assert rm.avail_cores == 8
    assert not rm._dvm_rank_allocations
    rm.reporting_file.close()
