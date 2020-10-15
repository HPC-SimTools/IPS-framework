from ipsframework import ips
import pytest
import mock
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
    MockFramework.assert_called_with(True, True, True, [], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--create-runspace"]
    ips.main()
    MockFramework.assert_called_with(True, False, False, [], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--create-runspace"]
    ips.main()
    MockFramework.assert_called_with(True, False, False, [], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--run-setup"]
    ips.main()
    MockFramework.assert_called_with(False, True, False, [], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--run"]
    ips.main()
    MockFramework.assert_called_with(False, False, True, [], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--simulation=sim.cfg"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, ['sim.cfg'], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim.cfg"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, ['sim.cfg'], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--config=sim1.cfg,sim2.cfg"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, ['sim1.cfg', 'sim2.cfg'], 'sys.stdout', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--simulation=sim1.cfg", "--sim_name=sim1,sim2"]
    ips.main()
    MockFramework.assert_not_called()

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--log=file.log"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, [], 'file.log', '', [], False, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--nodes=5", "--ppn=32"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, [], 'sys.stdout', '', [], False, False, 5, 32)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--debug"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, [], 'sys.stdout', '', [], True, False, 0, 0)

    MockFramework.reset_mock()
    sys.argv = ["ips.py", "--verbose"]
    ips.main()
    MockFramework.assert_called_with(True, True, True, [], 'sys.stdout', '', [], False, True, 0, 0)