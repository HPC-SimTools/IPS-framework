"""CPU-budget tests use explicit scheduler data, never the test host's hwloc."""

from unittest import mock

import pytest

from ipsframework._internal.cpu_resources import (
    _ensemble_worker_threads,
    _expand_slurm_counts,
    _get_cpu_nodes,
)


def _parameters(**overrides):
    """Create a configuration lookup.

    :param overrides: Platform settings to override.
    :returns: Lookup accepting optional service keyword arguments.
    """
    values = {'NODE_DETECTION': 'manual', 'CORES_PER_NODE': 8, 'NODES': 2, 'PROCS_PER_NODE': 2}
    values.update(overrides)
    return lambda name, **kwargs: values.get(name)


@pytest.mark.parametrize('hwthreads', [False, True])
def test_manual_budget_is_independent_of_slots(hwthreads: bool) -> None:
    """Manual budgets already use the selected CPU unit.

    :param hwthreads: Selected allocation mode.
    :returns: None.
    """
    assert _get_cpu_nodes(_parameters(), hwthreads) == [('dummynode0', 8), ('dummynode1', 8)]


@pytest.mark.parametrize('hwthreads,expected', [(False, [128, 32]), (True, [256, 64])])
def test_slurm_restricted_allocation(monkeypatch, hwthreads: bool, expected: list[int]) -> None:
    """Restrict capacity using remote Slurm topology and granted CPU counts.

    :param monkeypatch: Environment and subprocess fixture.
    :param hwthreads: Selected allocation mode.
    :param expected: Expected per-node capacities.
    :returns: None.
    """
    monkeypatch.setenv('SLURM_JOB_NODELIST', 'nid[1-2]')
    monkeypatch.setenv('SLURM_JOB_CPUS_PER_NODE', '256,64')
    topology = '\n'.join(
        f'NodeName=nid{i} CPUTot=256 Sockets=2 CoresPerSocket=64 ThreadsPerCore=2' for i in (1, 2)
    )
    query = mock.Mock(side_effect=['nid1\nnid2\n', topology])
    monkeypatch.setattr('ipsframework._internal.cpu_resources.subprocess.check_output', query)
    assert _get_cpu_nodes(
        _parameters(NODE_DETECTION='slurm_env', CORES_PER_NODE=128), hwthreads
    ) == list(zip(['nid1', 'nid2'], expected, strict=True))
    assert query.call_count == 2


@pytest.mark.parametrize('hwthreads,expected', [(False, 4), (True, 8)])
def test_slurm_core_counted_cpus(monkeypatch, hwthreads: bool, expected: int) -> None:
    """Support Slurm configured to count cores rather than SMT threads.

    :param monkeypatch: Environment and subprocess fixture.
    :param hwthreads: Selected allocation mode.
    :param expected: Expected capacity.
    :returns: None.
    """
    monkeypatch.setenv('SLURM_JOB_NODELIST', 'node1')
    monkeypatch.setenv('SLURM_JOB_CPUS_PER_NODE', '4')
    monkeypatch.setattr(
        'ipsframework._internal.cpu_resources.subprocess.check_output',
        mock.Mock(
            side_effect=[
                'node1',
                'NodeName=node1 CPUTot=8 Sockets=2 CoresPerSocket=4 ThreadsPerCore=2',
            ]
        ),
    )
    assert _get_cpu_nodes(_parameters(NODE_DETECTION='slurm_env'), hwthreads) == [
        ('node1', expected)
    ]


def test_slurm_counts() -> None:
    """Validate compressed CPU counts.

    :returns: None.
    """
    assert _expand_slurm_counts('256(x2),64') == [256, 256, 64]
    for invalid in ('0', '2(x0)', 'abc', '2,'):
        with pytest.raises(ValueError):
            _expand_slurm_counts(invalid)


@pytest.mark.parametrize(
    'capacities,budget,expected',
    [([128, 128], 8, 16), ([128], 1, 128), ([256], 8, 32), ([128, 32], 8, 4)],
)
def test_ensemble_concurrency(capacities: list[int], budget: int, expected: int) -> None:
    """Compute concurrency in the chosen CPU unit.

    :param capacities: Available CPUs per worker.
    :param budget: Per-instance CPU budget.
    :param expected: Safe uniform concurrency.
    :returns: None.
    """
    assert _ensemble_worker_threads(capacities, budget) == expected


@pytest.mark.parametrize('budget', [0, -1, True, 1.5, 129])
def test_invalid_ensemble_budget(budget) -> None:
    """Reject invalid or oversized instance budgets.

    :param budget: Invalid per-instance budget.
    :returns: None.
    """
    with pytest.raises(ValueError):
        _ensemble_worker_threads([128], budget)


def test_slurm_missing_topology_is_not_local_fallback(monkeypatch) -> None:
    """Missing remote topology must not substitute the Mac's CPU count.

    :param monkeypatch: Fixture supplying deliberately incomplete Slurm data.
    :returns: None.
    """
    monkeypatch.setenv('SLURM_JOB_NODELIST', 'node1')
    monkeypatch.setenv('SLURM_JOB_CPUS_PER_NODE', '8')
    monkeypatch.setattr(
        'ipsframework._internal.cpu_resources.subprocess.check_output',
        mock.Mock(side_effect=['node1', 'NodeName=node1 CPUTot=256']),
    )
    with pytest.raises(ValueError, match='Missing Slurm CPU topology'):
        _get_cpu_nodes(_parameters(NODE_DETECTION='slurm_env'))


def test_slurm_mismatched_counts(monkeypatch) -> None:
    """Reject mismatched scheduler node/count records.

    :param monkeypatch: Fixture supplying malformed Slurm data.
    :returns: None.
    """
    monkeypatch.setenv('SLURM_JOB_NODELIST', 'node[1-2]')
    monkeypatch.setenv('SLURM_JOB_CPUS_PER_NODE', '8')
    monkeypatch.setattr(
        'ipsframework._internal.cpu_resources.subprocess.check_output',
        mock.Mock(return_value='node1 node2'),
    )
    with pytest.raises(ValueError, match='different lengths'):
        _get_cpu_nodes(_parameters(NODE_DETECTION='slurm_env'))
