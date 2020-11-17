from ipsframework import ips
import pytest
from unittest import mock
import sys


def test_ips_main_empty(capfd):
    # override sys.argv for testing
    sys.argv = ["ips.py"]

    with pytest.raises(SystemExit) as e:
        ips.main()
    assert e.value.code == 1
    captured = capfd.readouterr()
    assert captured.out == 'Need to specify a platform file\n'
    assert captured.err == ''


@mock.patch('ipsframework.ips.Framework')
def test_ips_main(MockFramework):

    # override sys.argv for testing
    sys.argv = ["ips.py"]
    ips.main()
    MockFramework.assert_called_with([], 'sys.stdout', '', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--simulation=sim.cfg"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', '', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg"]
    ips.main()
    MockFramework.assert_called_with(['sim.cfg'], 'sys.stdout', '', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim1.cfg,sim2.cfg"]
    ips.main()
    MockFramework.assert_called_with(['sim1.cfg', 'sim2.cfg'], 'sys.stdout', '', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--log=file.log"]
    ips.main()
    MockFramework.assert_called_with([], 'file.log', '', False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--nodes=5", "--ppn=32"]
    ips.main()
    MockFramework.assert_called_with([], 'sys.stdout', '', False, False, 5, 32)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--debug"]
    ips.main()
    MockFramework.assert_called_with([], 'sys.stdout', '', True, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--verbose"]
    ips.main()
    MockFramework.assert_called_with([], 'sys.stdout', '', False, True, 0, 0)
