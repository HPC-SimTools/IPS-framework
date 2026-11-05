"""DVM diagnostics and cleanup without requiring PRTE or Slurm."""

import json
import logging
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ipsframework import services


def records(worker):
    return [json.loads(line) for line in worker.dvm_diagnostics.path.read_text().splitlines()]


@pytest.fixture
def running(tmp_path, monkeypatch):
    monkeypatch.setenv('PMIX_SERVER_URI41', 'test-original')
    monkeypatch.setenv('PRTE_MCA_ras_slurm_use_entire_allocation', '0')
    monkeypatch.setenv('PRTE_MCA_rmaps_default_mapping_policy', 'core')
    proc = Mock(pid=123, returncode=None)
    proc.poll.side_effect = lambda: proc.returncode

    def popen(command, **kwargs):
        Path(command[-1]).write_text('test-uri\n')
        return proc

    monkeypatch.setattr(services.subprocess, 'Popen', popen)
    monkeypatch.setattr(services.shutil, 'which', lambda name: '/bin/' + name)
    worker = SimpleNamespace(address='tcp://worker:1234')
    plugin = services.DVMPlugin(logging.getLogger(__name__), tmp_path)
    plugin.setup(worker)
    yield plugin, worker, proc
    worker.dvm_log.close()


def test_ready_and_graceful_shutdown(running, monkeypatch):
    plugin, worker, proc = running

    def stop(*args, **kwargs):
        proc.returncode = 0
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(services.subprocess, 'run', stop)
    plugin.teardown(worker)
    events = records(worker)
    assert [r['event'] for r in events] == [
        'launch_requested',
        'launched',
        'ready',
        'shutdown_begin',
        'shutdown_command',
        'exit_observed',
        'shutdown_command_end',
        'shutdown_complete',
    ]
    assert events[0]['environment']['PRTE_MCA_ras_slurm_use_entire_allocation'] == '1'
    assert events[2]['uri'] == 'test-uri'
    assert events[5]['shutdown_requested'] is True
    proc.terminate.assert_not_called()
    proc.kill.assert_not_called()
    assert worker.dvm_log.closed
    assert (worker.dvm_diagnostics.directory / 'shutdown.log').exists()


def test_shutdown_timeout_escalates_and_reaps(running, monkeypatch):
    plugin, worker, proc = running
    monkeypatch.setattr(
        services.subprocess, 'run', Mock(side_effect=subprocess.TimeoutExpired('pterm', 10))
    )
    calls = []

    def wait(timeout):
        calls.append(timeout)
        if len(calls) < 3:
            raise subprocess.TimeoutExpired('prte', timeout)
        proc.returncode = -9
        return -9

    proc.wait.side_effect = wait
    plugin.teardown(worker)
    assert calls == [10, 5, 5]
    proc.terminate.assert_called_once()
    proc.kill.assert_called_once()
    events = records(worker)
    assert {'shutdown_command_failed', 'terminate_requested', 'kill_requested'} <= {
        e['event'] for e in events
    }
    assert events[-1]['signal'] == 9
    assert events[-1]['dvm_return_code'] == -9


def test_unexpected_exit_observed_once(running):
    plugin, worker, proc = running
    proc.returncode = 195
    worker.dvm_diagnostics.record('instance_end', instance='INSTANCE_1', return_code=1)
    plugin.teardown(worker)
    exits = [r for r in records(worker) if r['event'] == 'exit_observed']
    assert len(exits) == 1
    assert exits[0]['shutdown_requested'] is False
    assert exits[0]['dvm_return_code'] == 195
    proc.terminate.assert_not_called()


def test_launch_failure_is_recorded_and_closed(tmp_path, monkeypatch):
    monkeypatch.setenv('PRTE_MCA_ras_slurm_use_entire_allocation', '0')
    monkeypatch.setenv('PRTE_MCA_rmaps_default_mapping_policy', 'core')
    monkeypatch.setattr(services.subprocess, 'Popen', Mock(side_effect=OSError('missing prte')))
    worker = SimpleNamespace(address='worker')
    plugin = services.DVMPlugin(logging.getLogger(__name__), tmp_path)
    with pytest.raises(OSError, match='missing prte'):
        plugin.setup(worker)
    assert 'startup_failed' in [r['event'] for r in records(worker)]
    assert worker.dvm_log.closed


def test_child_failure_references_dvm(tmp_path, monkeypatch):
    monkeypatch.setenv('IPS_DVM_DIAGNOSTICS', '/run/dvm/id/lifecycle.jsonl')
    monkeypatch.setenv('IPS_DVM_INSTANCE', 'INSTANCE_3')
    proxy = Mock()
    proxy.get_working_dir.return_value = str(tmp_path)
    task = Mock(
        start_time=0, nproc=1, cores_allocated=1, binary='prun', args=(), command='prun test'
    )
    task.process.wait.return_value = 195
    proxy.task_map = {7: task}
    assert services.ServicesProxy.wait_task(proxy, 7) == 195
    failure = json.loads(next(tmp_path.glob('dvm-failures.*.jsonl')).read_text())
    assert failure['instance'] == 'INSTANCE_3'
    assert failure['return_code'] == 195
    assert failure['dvm_lifecycle'] == '/run/dvm/id/lifecycle.jsonl'
    assert failure['dvm_state'] == 'unknown_in_child'


@pytest.mark.parametrize('return_code', [0, 1, 195])
def test_instance_correlated_with_worker_state(running, monkeypatch, tmp_path, return_code):
    _, worker, dvm = running
    worker.name = 'worker'
    worker.get_current_task = lambda: 'INSTANCE_4'
    worker.log_event = Mock()
    monkeypatch.setattr(services, 'get_worker', lambda: worker)
    child = Mock(returncode=return_code)

    def communicate(**kwargs):
        if return_code:
            dvm.returncode = 195
        return '', ''

    child.communicate.side_effect = communicate
    popen = Mock(return_value=child)
    monkeypatch.setattr(services.subprocess, 'Popen', popen)
    services.launch('ips.py', 'INSTANCE_4', tmp_path)
    env = popen.call_args.kwargs['env']
    assert env['IPS_DVM_DIAGNOSTICS'] == str(worker.dvm_diagnostics.path)
    assert env['IPS_DVM_INSTANCE'] == 'INSTANCE_4'
    event = records(worker)[-1]
    assert event['event'] == 'instance_end'
    assert event['return_code'] == return_code
    assert event['dvm_state'] == ('exited' if return_code else 'running')
    assert worker.log_event.call_args.args[1]['state'] == ('Failed' if return_code else 'Succeeded')


def test_missing_shutdown_command_escalates(running, monkeypatch):
    plugin, worker, proc = running
    monkeypatch.setattr(services.shutil, 'which', lambda name: None)
    count = 0

    def wait(timeout):
        nonlocal count
        count += 1
        if count == 1:
            raise subprocess.TimeoutExpired('prte', timeout)
        proc.returncode = -15
        return -15

    proc.wait.side_effect = wait
    plugin.teardown(worker)
    assert 'shutdown_command_unavailable' in [r['event'] for r in records(worker)]
    proc.terminate.assert_called_once()
    proc.kill.assert_not_called()
