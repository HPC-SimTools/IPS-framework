import os
import sys
from unittest import mock

import pytest

from ipsframework import ips


@mock.patch('ipsframework.ips.Framework')
def test_ips_main(mock_framework):
    # override sys.argv for testing
    sys.argv = ['ips.py']
    with pytest.raises(SystemExit) as excinfo:
        ips.main()
    assert excinfo.value.code == 2
    mock_framework.assert_not_called()

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--simulation=sim.cfg']
    with pytest.raises(SystemExit) as excinfo:
        ips.main()
    assert excinfo.value.code == 2
    mock_framework.assert_not_called()

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--platform=platform.conf']
    with pytest.raises(SystemExit) as excinfo:
        ips.main()
    assert excinfo.value.code == 2
    mock_framework.assert_not_called()

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--simulation=sim.cfg', '--platform=platform.conf']
    ips.main()
    mock_framework.assert_called_with(
        ['sim.cfg'], 'sys.stdout', 'platform.conf', False, False, 0, 0
    )

    os.environ['IPS_PLATFORM_FILE'] = 'platform.conf'
    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim.cfg']
    ips.main()
    mock_framework.assert_called_with(
        ['sim.cfg'], 'sys.stdout', 'platform.conf', False, False, 0, 0
    )

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim1.cfg,sim2.cfg']
    ips.main()
    mock_framework.assert_called_with(
        ['sim1.cfg', 'sim2.cfg'], 'sys.stdout', 'platform.conf', False, False, 0, 0
    )

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim.cfg', '--log=file.log']
    ips.main()
    mock_framework.assert_called_with(['sim.cfg'], 'file.log', 'platform.conf', False, False, 0, 0)

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim.cfg', '--nodes=5', '--ppn=32']
    ips.main()
    mock_framework.assert_called_with(
        ['sim.cfg'], 'sys.stdout', 'platform.conf', False, False, 5, 32
    )

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim.cfg', '--debug']
    ips.main()
    mock_framework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', True, False, 0, 0)

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim.cfg', '--verbose']
    ips.main()
    mock_framework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', False, True, 0, 0)

    mock_framework.reset_mock()
    sys.argv = ['ips.py', '--config=sim.cfg', '--platform=workstation.conf']
    ips.main()
    mock_framework.assert_called_with(
        ['sim.cfg'], 'sys.stdout', 'workstation.conf', False, False, 0, 0
    )
