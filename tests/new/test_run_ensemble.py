import logging
import os

from ipsframework import ServicesProxy, TaskPool
from ipsframework import services as services_module


class DummyFramework:
    logger = logging.getLogger(__name__)


class DummyDaskWorker:
    name = 'worker_0'

    def get_current_task(self):
        return 'task-key'

    def log_event(self, topic, event):
        pass


def write_stdout_stderr_script(tmpdir):
    script = tmpdir.join('write_stdout_stderr.sh')
    script.write('#!/bin/sh\necho stdout-line\necho stderr-line >&2\n')
    script.chmod(448)  # 700
    return script


def test_run_ensemble_passes_logfile_and_errfile_to_add_task(tmpdir, monkeypatch):
    template = tmpdir.join('template.config')
    template.write('[comp]\nA = ?\n')
    run_dir = tmpdir.mkdir('runs')

    services = ServicesProxy(None, None, None, {'USE_PORTAL': 'False'}, None)
    services.fwk = DummyFramework()
    services.logger = logging.getLogger(__name__)

    submitted_kwargs = []
    submit_tasks_kwargs = []

    def record_add_task(task_pool_name, task_name, nproc, working_dir, binary, *args, **kwargs):
        submitted_kwargs.append(kwargs)

    def record_submit_tasks(*args, **kwargs):
        submit_tasks_kwargs.append(kwargs)
        return 1

    monkeypatch.setattr(services, 'create_task_pool', lambda name: None)
    monkeypatch.setattr(services, 'add_task', record_add_task)
    monkeypatch.setattr(services, 'submit_tasks', record_submit_tasks)
    monkeypatch.setattr(services, 'get_finished_tasks', lambda task_pool_name: {})
    monkeypatch.setattr(services, 'remove_task_pool', lambda task_pool_name: None)

    services.run_ensemble(
        template,
        {'comp': {'A': ['1', '2']}},
        run_dir,
        'ensemble',
        num_nodes=1,
        logfile='instance.out',
        errfile='instance.err',
    )

    assert submitted_kwargs == [
        {'logfile': 'instance.out', 'errfile': 'instance.err'},
        {'logfile': 'instance.out', 'errfile': 'instance.err'},
    ]
    assert submit_tasks_kwargs == [
        {
            'block': True,
            'use_dask': True,
            'dask_nodes': 1,
            'dask_ppw': None,
            'oversubscribe': False,
            'hwthreads': False,
            'logfile': 'instance.out',
            'errfile': 'instance.err',
        }
    ]


def test_services_submit_tasks_passes_logfile_and_errfile_to_task_pool():
    services = ServicesProxy(None, None, None, {'USE_PORTAL': 'False'}, None)
    services.logger = logging.getLogger(__name__)

    class DummyTaskPool:
        def __init__(self):
            self.submit_args = None

        def submit_tasks(self, *args):
            self.submit_args = args
            return 1

    task_pool = DummyTaskPool()
    services.task_pools['pool'] = task_pool
    services._send_monitor_event = lambda *args, **kwargs: None

    assert services.submit_tasks('pool', logfile='instance.out', errfile='instance.err') == 1
    assert task_pool.submit_args[-2:] == ('instance.out', 'instance.err')


def test_task_pool_submit_tasks_passes_logfile_and_errfile_to_dask(monkeypatch):
    services = ServicesProxy(None, None, None, {'USE_PORTAL': 'False'}, None)
    task_pool = TaskPool('pool', services)
    task_pool.serial_pool = True
    submitted_args = []

    def record_submit_dask_tasks(*args):
        submitted_args.append(args)
        return 1

    monkeypatch.setattr(TaskPool, 'dask', object())
    monkeypatch.setattr(TaskPool, 'distributed', object())
    monkeypatch.setattr(task_pool, 'submit_dask_tasks', record_submit_dask_tasks)

    assert (
        task_pool.submit_tasks(use_dask=True, logfile='instance.out', errfile='instance.err') == 1
    )
    assert submitted_args[0][-2:] == ('instance.out', 'instance.err')


def test_task_pool_launch_keywords_use_logfile_and_errfile_defaults():
    keywords = TaskPool._launch_keywords_with_defaults(
        {'block': False},
        logfile='instance.out',
        errfile='instance.err',
    )

    assert keywords == {
        'block': False,
        'logfile': 'instance.out',
        'errfile': 'instance.err',
    }


def test_task_pool_launch_keywords_preserve_task_logfile_and_errfile():
    keywords = TaskPool._launch_keywords_with_defaults(
        {
            'block': False,
            'logfile': 'task.out',
            'errfile': 'task.err',
        },
        logfile='instance.out',
        errfile='instance.err',
    )

    assert keywords == {
        'block': False,
        'logfile': 'task.out',
        'errfile': 'task.err',
    }


def test_launch_mapped_task_passes_logfile_and_errfile_to_launch(monkeypatch):
    launch_calls = []

    def record_launch(executable, task_name, working_dir, *args, **kwargs):
        launch_calls.append((args, kwargs))

    monkeypatch.setattr(services_module, 'launch', record_launch)

    services_module.launch_mapped_task(
        '/bin/echo',
        'task_0',
        '/tmp',
        ['hello'],
        {'logfile': 'instance.out', 'errfile': 'instance.err'},
        1,
        None,
    )

    assert launch_calls == [
        (
            ('hello',),
            {
                'logfile': 'instance.out',
                'errfile': 'instance.err',
                'cpus_per_proc': 1,
                'worker_event_logfile': None,
            },
        )
    ]


def test_launch_writes_stderr_to_logfile_when_errfile_is_omitted(tmpdir, monkeypatch):
    script = write_stdout_stderr_script(tmpdir)

    def get_worker():
        return DummyDaskWorker()

    monkeypatch.setattr(services_module, 'get_worker', get_worker)

    assert services_module.launch(
        str(script),
        'task_0',
        str(tmpdir),
        logfile='task.log',
    ) == ('task_0', 0)

    assert tmpdir.join('task.log').readlines() == [
        'stdout-line\n',
        'stderr-line\n',
    ]


def test_launch_writes_stderr_to_logfile_when_errfile_matches_logfile(tmpdir, monkeypatch):
    script = write_stdout_stderr_script(tmpdir)

    def get_worker():
        return DummyDaskWorker()

    monkeypatch.setattr(services_module, 'get_worker', get_worker)

    assert services_module.launch(
        str(script),
        'task_0',
        str(tmpdir),
        logfile='task.log',
        errfile=os.path.join(str(tmpdir), 'task.log'),
    ) == ('task_0', 0)

    assert tmpdir.join('task.log').readlines() == [
        'stdout-line\n',
        'stderr-line\n',
    ]
