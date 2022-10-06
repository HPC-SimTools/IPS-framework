from unittest import mock
import io
import pytest
from ipsframework.resourceManager import ResourceManager
from ipsframework.ipsExceptions import (InsufficientResourcesException,
                                        BadResourceRequestException,
                                        ResourceRequestMismatchException,
                                        GPUResourceRequestMismatchException,
                                        ResourceRequestUnequalPartitioningException)


def test_allocations(tmpdir):
    fwk = mock.Mock()
    dm = mock.Mock()
    tm = mock.Mock()
    cm = mock.Mock()
    cm.fwk_sim_name = 'sim_name'
    cm.sim_map = {'sim_name': mock.Mock(sim_root=str(tmpdir))}
    cm.get_platform_parameter.return_value = 'HOST'

    rm = ResourceManager(fwk)
    rm.initialize(dm, tm, cm,
                  cmd_nodes=2,
                  cmd_ppn=4)

    for node in ('dummy_node0', 'dummy_node1'):
        with io.StringIO() as output:
            rm.nodes[node].print_sockets(output)
            lines = [s.strip() for s in output.getvalue().split('\n')]
            assert lines[0] == "socket: 0"
            assert lines[1] == "availablilty: 4"
            assert lines[2] == "task ids: []"
            assert lines[3] == "owners: []"
            assert lines[4] == "cores: 4"
            assert lines[5] == "core: 0  - available"
            assert lines[6] == "core: 1  - available"
            assert lines[7] == "core: 2  - available"
            assert lines[8] == "core: 3  - available"

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

    with pytest.raises(BadResourceRequestException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=12,
                          task_id=0,
                          whole_nodes=True,
                          whole_socks=False)

    assert str(excinfo.value) == "component comp0 requested 3 nodes, which is more than possible by 1 nodes, for task 0."

    with pytest.raises(ResourceRequestUnequalPartitioningException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=3,
                          task_id=0,
                          whole_nodes=True,
                          whole_socks=False,
                          task_ppn=2)

    assert (str(excinfo.value) == "component comp0 requested 3 processes with 2 processes per node, while the number of processes requested is "
            "less than the max (8), it will result in unequal partitioning of processes across nodes")

    with pytest.raises(BadResourceRequestException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=12,
                          task_id=0,
                          whole_nodes=False,
                          whole_socks=True)

    assert str(excinfo.value) == "component comp0 requested 3 nodes, which is more than possible by 1 nodes, for task 0."

    with pytest.raises(ResourceRequestMismatchException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=6,
                          task_id=0,
                          whole_nodes=False,
                          whole_socks=False,
                          task_ppn=2)

    assert (str(excinfo.value) == "component comp0 requested 6 processes with 2 processes per node, while the number of processes requested is "
            "less than the max (8), the processes per node value is too low.")

    rm.get_allocation(comp_id='comp0',
                      nproc=2,
                      task_id=0,
                      whole_nodes=False,
                      whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 2"
        assert lines[2] == "task ids: [0]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 0  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 0  - owner: comp0"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 4"
        assert lines[2] == "task ids: []"
        assert lines[3] == "owners: []"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    rm.get_allocation(comp_id='comp0',
                      nproc=2,
                      task_id=1,
                      whole_nodes=True,
                      whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 2"
        assert lines[2] == "task ids: [0]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 0  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 0  - owner: comp0"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [1]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 1  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 1  - owner: comp0"
        assert lines[7] == "core: 2  - task_id: 1  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 1  - owner: comp0"

    rm.get_allocation(comp_id='comp0',
                      nproc=2,
                      task_id=2,
                      whole_nodes=False,
                      whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [0, 2]"
        assert lines[3] == "owners: ['comp0', 'comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 0  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 0  - owner: comp0"
        assert lines[7] == "core: 2  - task_id: 2  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 2  - owner: comp0"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [1]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 1  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 1  - owner: comp0"
        assert lines[7] == "core: 2  - task_id: 1  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 1  - owner: comp0"

    with pytest.raises(InsufficientResourcesException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=1,
                          task_id=3,
                          whole_nodes=False,
                          whole_socks=False)

    assert str(excinfo.value) == "component comp0 requested 1 nodes, which is more than available by 0 nodes, for task 3."

    rm.release_allocation(task_id=1,
                          status=None)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [0, 2]"
        assert lines[3] == "owners: ['comp0', 'comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 0  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 0  - owner: comp0"
        assert lines[7] == "core: 2  - task_id: 2  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 2  - owner: comp0"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 4"
        assert lines[2] == "task ids: []"
        assert lines[3] == "owners: []"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    rm.release_allocation(task_id=0,
                          status=None)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 2"
        assert lines[2] == "task ids: [2]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - task_id: 2  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 2  - owner: comp0"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 4"
        assert lines[2] == "task ids: []"
        assert lines[3] == "owners: []"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    rm.release_allocation(task_id=2,
                          status=None)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 4"
        assert lines[2] == "task ids: []"
        assert lines[3] == "owners: []"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 4"
        assert lines[2] == "task ids: []"
        assert lines[3] == "owners: []"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    rm.get_allocation(comp_id='comp1',
                      nproc=2,
                      task_id=9,
                      whole_nodes=False,
                      whole_socks=True)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [9]"
        assert lines[3] == "owners: ['comp1']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 9  - owner: comp1"
        assert lines[6] == "core: 1  - task_id: 9  - owner: comp1"
        assert lines[7] == "core: 2  - task_id: 9  - owner: comp1"
        assert lines[8] == "core: 3  - task_id: 9  - owner: comp1"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 4"
        assert lines[2] == "task ids: []"
        assert lines[3] == "owners: []"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - available"
        assert lines[6] == "core: 1  - available"
        assert lines[7] == "core: 2  - available"
        assert lines[8] == "core: 3  - available"

    # test GPUs
    with pytest.raises(GPUResourceRequestMismatchException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=1,
                          task_gpp=1,
                          task_id=0,
                          whole_nodes=True,
                          whole_socks=False)

    assert str(excinfo.value) == "component comp0 requested 1 processes per node with 1 GPUs per process, which is greater than the available 0 GPUS_PER_NODE"

    # set GPUS_PER_NODE to 2
    rm = ResourceManager(fwk)
    rm.initialize(dm, tm, cm,
                  cmd_nodes=2,
                  cmd_ppn=4)
    rm.gpn = 2

    with pytest.raises(GPUResourceRequestMismatchException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=1,
                          task_gpp=4,
                          task_id=0,
                          whole_nodes=True,
                          whole_socks=False)

    assert str(excinfo.value) == "component comp0 requested 1 processes per node with 4 GPUs per process, which is greater than the available 2 GPUS_PER_NODE"

    with pytest.raises(GPUResourceRequestMismatchException) as excinfo:
        rm.get_allocation(comp_id='comp0',
                          nproc=2,
                          task_gpp=2,
                          task_id=0,
                          whole_nodes=True,
                          whole_socks=False)

    assert str(excinfo.value) == "component comp0 requested 2 processes per node with 2 GPUs per process, which is greater than the available 2 GPUS_PER_NODE"

    rm.get_allocation(comp_id='comp0',
                      nproc=2,
                      task_ppn=1,
                      task_gpp=2,
                      task_id=0,
                      whole_nodes=True,
                      whole_socks=False)

    with io.StringIO() as output:
        rm.nodes['dummy_node0'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [0]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 0  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 0  - owner: comp0"
        assert lines[7] == "core: 2  - task_id: 0  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 0  - owner: comp0"

    with io.StringIO() as output:
        rm.nodes['dummy_node1'].print_sockets(output)
        lines = [s.strip() for s in output.getvalue().split('\n')]
        assert lines[0] == "socket: 0"
        assert lines[1] == "availablilty: 0"
        assert lines[2] == "task ids: [0]"
        assert lines[3] == "owners: ['comp0']"
        assert lines[4] == "cores: 4"
        assert lines[5] == "core: 0  - task_id: 0  - owner: comp0"
        assert lines[6] == "core: 1  - task_id: 0  - owner: comp0"
        assert lines[7] == "core: 2  - task_id: 0  - owner: comp0"
        assert lines[8] == "core: 3  - task_id: 0  - owner: comp0"
