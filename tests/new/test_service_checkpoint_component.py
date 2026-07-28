from unittest.mock import MagicMock

import pytest

from ipsframework import ServicesProxy


def test_checkpoint_components_bad_input():
    # empty sim_conf
    sim_conf = {}
    services_proxy = ServicesProxy(None, None, None, sim_conf, None)
    services_proxy.error = MagicMock(name='error')
    services_proxy.exception = MagicMock(name='exception')
    services_proxy._dispatch_checkpoint = MagicMock(name='dispatch_checkpoint')

    with pytest.raises(KeyError) as excinfo:
        services_proxy.checkpoint_components([], 0)
    assert str(excinfo.value) == "'CHECKPOINT'"

    services_proxy.error.assert_called_with(
        'Missing CHECKPOINT config section, or one of the required parameters: MODE, NUM_CHECKPOINT'
    )
    services_proxy.exception.assert_called_with('Error accessing CHECKPOINT section in config file')
    services_proxy._dispatch_checkpoint.assert_not_called()

    # missing NUM_CHECKPOINT
    services_proxy.sim_conf = {'CHECKPOINT': {'MODE': 'ALL'}}
    with pytest.raises(KeyError) as excinfo:
        services_proxy.checkpoint_components([], 0)
    assert str(excinfo.value) == "'NUM_CHECKPOINT'"

    services_proxy.error.assert_called_with(
        'Missing CHECKPOINT config section, or one of the required parameters: MODE, NUM_CHECKPOINT'
    )
    services_proxy.exception.assert_called_with('Error accessing CHECKPOINT section in config file')
    services_proxy._dispatch_checkpoint.assert_not_called()

    # invalid MODE
    services_proxy.sim_conf = {'CHECKPOINT': {'MODE': 'NOT_A_MODE', 'NUM_CHECKPOINT': '-1'}}
    with pytest.raises(Exception) as excinfo:
        services_proxy.checkpoint_components([], 0)
    assert str(excinfo.value) == 'Invalid MODE = NOT_A_MODE in checkpoint configuration'

    services_proxy.error.assert_called_with(
        'Invalid MODE = %s in checkpoint configuration', 'NOT_A_MODE'
    )
    services_proxy._dispatch_checkpoint.assert_not_called()


def test_checkpoint_components_force():
    # with Force=True, it should always call _dispatch_checkpoint

    services_proxy = ServicesProxy(None, None, None, {}, None)
    services_proxy._dispatch_checkpoint = MagicMock(name='dispatch_checkpoint')
    services_proxy.checkpoint_components([], 0, Force=True)
    services_proxy._dispatch_checkpoint.assert_called_once_with(0, [], False)


def test_checkpoint_components_num_checkpoint(tmpdir):
    # NUM_CHECKPOINT=0, no checkpointing

    sim_conf = {'CHECKPOINT': {'MODE': 'ALL', 'NUM_CHECKPOINT': '0'}, 'SIM_ROOT': '/some_dir'}
    services_proxy = ServicesProxy(None, None, None, sim_conf, None)
    services_proxy.error = MagicMock(name='error')
    services_proxy.debug = MagicMock(name='debug')
    services_proxy._send_monitor_event = MagicMock(name='_send_monitor_event')
    ret_dict = services_proxy.checkpoint_components([], 0)
    assert ret_dict is None  # should be None since no checkpoint should happen
    services_proxy._send_monitor_event.assert_not_called()

    # NUM_CHECKPOINT=-1, checkpoint runs, keeping all checkpoints, no removing
    services_proxy.sim_conf = {
        'CHECKPOINT': {'MODE': 'ALL', 'NUM_CHECKPOINT': '-1'},
        'SIM_ROOT': '/some_dir',
    }
    ret_dict = services_proxy.checkpoint_components([], 0)
    assert ret_dict == {}  # should be empty since no components
    services_proxy._send_monitor_event.assert_called_with('IPS_CHECKPOINT_START', 'Components = []')

    # NUM_CHECKPOINT=3, checkpoint runs, keeping only the most recent 3 checkpoints
    # create restart folder and add 10 timestamp checkpoints
    restart_dir = tmpdir.mkdir('restart')
    for t in range(1, 11):
        restart_dir.mkdir(f'{t:.3f}')
    assert len(restart_dir.listdir()) == 10
    services_proxy.sim_conf = {
        'CHECKPOINT': {'MODE': 'ALL', 'NUM_CHECKPOINT': '3'},
        'SIM_ROOT': str(tmpdir),
    }
    ret_dict = services_proxy.checkpoint_components([], 10)
    assert ret_dict == {}  # should be empty since no components
    services_proxy._send_monitor_event.assert_called_with('IPS_CHECKPOINT_END', 'Components = []')

    # there should be only 3 remaining folder in restart (7, 8, 9)
    assert len(restart_dir.listdir()) == 3
    restart_checkpoints = [d.basename for d in restart_dir.listdir()]
    for n in ('8.000', '9.000', '10.000'):
        assert n in restart_checkpoints

    # Now try with PROTECT_FREQUENCY
    for t in range(11, 21):
        restart_dir.mkdir(f'{t:.3f}')
    assert len(restart_dir.listdir()) == 13
    services_proxy.sim_conf = {
        'CHECKPOINT': {'MODE': 'ALL', 'NUM_CHECKPOINT': '3', 'PROTECT_FREQUENCY': '2'},
        'SIM_ROOT': str(tmpdir),
    }
    services_proxy.chkpt_counter = 19
    services_proxy.new_chkpts = [f'{t:.3f}' for t in range(11, 21)]
    services_proxy.protected_chkpts = [f'{t:.3f}' for t in [12, 14, 16, 18]]

    ret_dict = services_proxy.checkpoint_components([], 20)
    assert ret_dict == {}  # should be empty since no components
    services_proxy._send_monitor_event.assert_called_with('IPS_CHECKPOINT_END', 'Components = []')

    # there should be every second from 12 and the 3 last non-protected checkpoints
    assert len(restart_dir.listdir()) == 8
    restart_checkpoints = [d.basename for d in restart_dir.listdir()]
    for n in (12, 14, 15, 16, 17, 18, 19, 20):
        assert f'{n:.3f}' in restart_checkpoints


def test_checkpoint_components_modes():
    # ALL
    sim_conf = {'CHECKPOINT': {'MODE': 'ALL', 'NUM_CHECKPOINT': '-1'}, 'SIM_ROOT': '/some_dir'}
    services_proxy = ServicesProxy(None, None, None, sim_conf, None)
    services_proxy.error = MagicMock(name='error')
    services_proxy.debug = MagicMock(name='debug')
    services_proxy._dispatch_checkpoint = MagicMock(name='dispatch_checkpoint')
    services_proxy._get_elapsed_time = MagicMock(name='_get_elapsed_time', return_value=5)
    services_proxy.start_time = 1000.0
    services_proxy.last_ckpt_walltime = 1000.0
    services_proxy.cur_time = 1010.0
    services_proxy.checkpoint_components([], 0)
    services_proxy._dispatch_checkpoint.assert_called_once()

    # WALLTIME_REGULAR
    services_proxy._dispatch_checkpoint.reset_mock()
    # 10 walltime interval, but only an interval of 2 has passed, shouldn't checkpoint
    services_proxy.start_time = 1000.0
    services_proxy.last_ckpt_walltime = 1000.0
    services_proxy.cur_time = 1002.0
    services_proxy.sim_conf = {
        'CHECKPOINT': {
            'MODE': 'WALLTIME_REGULAR',
            'WALLTIME_INTERVAL': '10',
            'NUM_CHECKPOINT': '-1',
        },
        'SIM_ROOT': '/some_dir',
    }
    services_proxy.checkpoint_components([], 0)
    services_proxy._dispatch_checkpoint.assert_not_called()

    # 20 interval, so should call checkpoint
    services_proxy.cur_time = 1020.0
    services_proxy.checkpoint_components([], 0)
    services_proxy._dispatch_checkpoint.assert_called_once()

    # WALLTIME_EXPLICIT
    services_proxy._dispatch_checkpoint.reset_mock()
    # 10 walltime interval, but only an interval of 2 has passed, shouldn't checkpoint
    services_proxy._get_elapsed_time = MagicMock(name='_get_elapsed_time', return_value=2)
    services_proxy.start_time = 1000.0
    services_proxy.last_ckpt_walltime = 1000.0
    services_proxy.cur_time = 1002.0
    services_proxy.sim_conf = {
        'CHECKPOINT': {
            'MODE': 'WALLTIME_EXPLICIT',
            'WALLTIME_VALUES': '10 100',
            'NUM_CHECKPOINT': '-1',
        },
        'SIM_ROOT': '/some_dir',
    }
    services_proxy.checkpoint_components([], 0)
    services_proxy._dispatch_checkpoint.assert_not_called()

    # 20 elapsed time, so should call checkpoint
    services_proxy._get_elapsed_time = MagicMock(name='_get_elapsed_time', return_value=20)
    services_proxy.cur_time = 1020.0
    services_proxy.checkpoint_components([], 0)
    services_proxy._dispatch_checkpoint.assert_called_once()

    # 50 elapsed time, should not call checkpoint since we have already checkpointed onve in this interval
    services_proxy._get_elapsed_time = MagicMock(name='_get_elapsed_time', return_value=50)
    services_proxy.cur_time = 1050.0
    services_proxy.last_ckpt_walltime = 1020.0
    services_proxy.checkpoint_components([], 0)
    services_proxy._dispatch_checkpoint.assert_called_once()

    # PHYSTIME_REGULAR
    services_proxy.time_loop = [0, 10, 20, 30]
    services_proxy._dispatch_checkpoint.reset_mock()
    # physics time=10 interval=15, so should not call checkpoint
    services_proxy.sim_conf = {
        'CHECKPOINT': {
            'MODE': 'PHYSTIME_REGULAR',
            'PHYSTIME_INTERVAL': '15',
            'NUM_CHECKPOINT': '-1',
        },
        'SIM_ROOT': '/some_dir',
    }
    assert services_proxy.last_ckpt_phystime is None
    services_proxy.checkpoint_components([], 10)
    assert services_proxy.last_ckpt_phystime == 0
    services_proxy._dispatch_checkpoint.assert_not_called()

    services_proxy._dispatch_checkpoint.reset_mock()
    # physics time=20 interval=15, so should call checkpoint
    services_proxy.checkpoint_components([], 20)
    services_proxy._dispatch_checkpoint.assert_called_once()

    # PHYSTIME_EXPLICIT
    services_proxy._dispatch_checkpoint.reset_mock()
    services_proxy.sim_conf = {
        'CHECKPOINT': {
            'MODE': 'PHYSTIME_EXPLICIT',
            'PHYSTIME_VALUES': '10 100',
            'NUM_CHECKPOINT': '-1',
        },
        'SIM_ROOT': '/some_dir',
    }
    services_proxy.checkpoint_components([], 5)
    services_proxy._dispatch_checkpoint.assert_not_called()

    services_proxy.checkpoint_components([], 20)
    services_proxy._dispatch_checkpoint.assert_called_once()
    services_proxy.last_ckpt_phystime = 20

    services_proxy.checkpoint_components([], 50)
    services_proxy._dispatch_checkpoint.assert_called_once()
