from unittest import mock
import sys
import os
import pytest
from ipsframework import ips


@mock.patch('ipsframework.ips.Framework')
def test_ips_main(MockFramework):

    # override sys.argv for testing
    sys.argv = ["ips.py"]
    with pytest.raises(SystemExit) as excinfo:
        ips.main()
    assert excinfo.value.code == 2
    MockFramework.assert_not_called()

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--simulation=sim.cfg"]
    with pytest.raises(SystemExit) as excinfo:
        ips.main()
    assert excinfo.value.code == 2
    MockFramework.assert_not_called()

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--platform=platform.conf"]
    with pytest.raises(SystemExit) as excinfo:
        ips.main()
    assert excinfo.value.code == 2
    MockFramework.assert_not_called()

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--simulation=sim.cfg", "--platform=platform.conf"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', False, False, 0, 0)

    os.environ['IPS_PLATFORM_FILE'] = 'platform.conf'
    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim1.cfg,sim2.cfg"]
    ips.main()
    MockFramework.assert_called_with(['sim1.cfg', 'sim2.cfg'], 'sys.stdout', 'platform.conf', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg", "--log=file.log"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'file.log', 'platform.conf', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg", "--nodes=5", "--ppn=32"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', False, False, 5, 32)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg", "--debug"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', True, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg", "--verbose"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', 'platform.conf', False, True, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg", "--platform=workstation.conf"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', 'workstation.conf', False, False, 0, 0)
