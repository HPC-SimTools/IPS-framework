"""CPU budgets independent of MPI rank limits and local machine topology."""

import os
import re
import subprocess
from collections.abc import Callable
from typing import Any


def _expand_slurm_counts(value: str) -> list[int]:
    """Expand Slurm's per-node CPU counts.

    :param value: A count expression such as ``256(x2),128``.
    :returns: One positive CPU count per allocated node.
    :raises ValueError: If the expression is malformed.
    """
    counts = []
    for group in value.split(','):
        match = re.fullmatch(r'([1-9][0-9]*)(?:\(x([1-9][0-9]*)\))?', group.strip())
        if match is None:
            raise ValueError(f'Invalid SLURM_JOB_CPUS_PER_NODE: {value!r}')
        counts.extend([int(match[1])] * int(match[2] or 1))
    return counts


def _get_cpu_nodes(
    get_parameter: Callable[..., Any], hwthreads: bool = False
) -> list[tuple[str, int]]:
    """Read allocated CPU budgets without using process-slot counts as capacity.

    Manual configurations declare budgets in the selected processing-element
    unit. Slurm CPU counts are converted using the compute nodes' scheduler
    topology, never the topology of the host running IPS. For partial Slurm
    allocations, core-mode capacity is conservatively rounded down.

    :param get_parameter: Configuration lookup accepting ``silent=True``.
    :param hwthreads: Whether the allocation unit is a hardware thread.
    :returns: Node names and allocatable processing-element counts.
    :raises ValueError: If capacity or scheduler topology cannot be established.
    """
    detection = get_parameter('NODE_DETECTION', silent=True)
    configured = int(get_parameter('CORES_PER_NODE', silent=True) or 0)
    if configured < 1:
        raise ValueError('CPU budgeting requires a positive CORES_PER_NODE')
    if detection == 'manual':
        nodes = int(get_parameter('NODES', silent=True) or 1)
        if nodes < 1:
            raise ValueError('NODES must be positive')
        return [(f'dummynode{i}', configured) for i in range(nodes)]
    if detection != 'slurm_env':
        raise ValueError('CPU budgeting currently requires manual or slurm_env node detection')

    nodelist = os.environ.get('SLURM_JOB_NODELIST') or os.environ.get('SLURM_NODELIST')
    counts = os.environ.get('SLURM_JOB_CPUS_PER_NODE')
    if not nodelist or not counts:
        raise ValueError('Slurm CPU budgeting requires the job node list and CPUs per node')
    names = subprocess.check_output(
        ['scontrol', 'show', 'hostnames', nodelist], encoding='UTF-8'
    ).split()
    allocated = _expand_slurm_counts(counts)
    if len(names) != len(allocated):
        raise ValueError('Slurm node list and CPU counts have different lengths')
    topology = subprocess.check_output(
        ['scontrol', 'show', 'node', nodelist, '--oneliner'], encoding='UTF-8'
    )
    topologies = {}
    for line in topology.splitlines():
        fields = dict(part.split('=', 1) for part in line.split() if '=' in part)
        if 'NodeName' in fields:
            topologies[fields['NodeName']] = fields
    result = []
    for name, granted in zip(names, allocated, strict=True):
        fields = topologies.get(name, {})
        try:
            tpc = int(fields['ThreadsPerCore'])
            physical = int(fields['Sockets']) * int(fields['CoresPerSocket'])
            scheduled = int(fields['CPUTot'])
        except (KeyError, ValueError) as exc:
            raise ValueError(f'Missing Slurm CPU topology for {name}') from exc
        if min(tpc, physical, scheduled) < 1 or scheduled not in (physical, physical * tpc):
            raise ValueError(f'Inconsistent Slurm CPU topology for {name}')
        # Slurm may count schedulable CPUs as cores or hardware threads.
        scheduled_per_core = scheduled // physical
        if hwthreads:
            capacity = min(configured, physical) * tpc
            capacity = min(capacity, granted * tpc // scheduled_per_core)
        else:
            capacity = min(configured, physical, granted // scheduled_per_core)
        if capacity < 1:
            raise ValueError(f'No complete processing element available on {name}')
        result.append((name, capacity))
    return result


def _ensemble_worker_threads(capacities: list[int], budget: int) -> int:
    """Compute a safe uniform concurrency for one Dask worker per node.

    :param capacities: Allocated CPU budgets of the worker nodes.
    :param budget: Processing elements reserved for each ensemble instance.
    :returns: Instances allowed concurrently on each worker.
    :raises ValueError: If the budget is invalid or cannot fit every worker.
    """
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ValueError('cores_per_instance must be a positive integer')
    if not capacities or min(capacities) < budget:
        raise ValueError('cores_per_instance exceeds the allocated CPU capacity of a worker node')
    return min(capacities) // budget
