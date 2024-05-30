import glob
import json
import os
import shutil
import sys
from unittest import mock

import pytest

from ipsframework import ips_dakota_dynamic


def copy_config_and_replace(infile, outfile, tmpdir):
    with open(infile, 'r') as fin:
        with open(outfile, 'w') as fout:
            for line in fin:
                if 'SCRIPT' in line:
                    fout.write(line.replace('$PWD', str(tmpdir)))
                elif line.startswith('SIM_ROOT'):
                    fout.write(f'SIM_ROOT = {tmpdir}/$SIM_NAME\n')
                else:
                    fout.write(line)


@pytest.mark.skipif(shutil.which('dakota') is None, reason='Requires dakota to run this test')
@pytest.mark.timeout(200)
def test_dakota(tmpdir):
    data_dir = os.path.dirname(__file__)
    copy_config_and_replace(os.path.join(data_dir, 'dakota_test_Gaussian.ips'), tmpdir.join('dakota_test_Gaussian.ips'), tmpdir)
    shutil.copy(os.path.join(data_dir, 'workstation.conf'), tmpdir)
    shutil.copy(os.path.join(data_dir, 'dakota_test_Gaussian.in'), tmpdir)
    shutil.copy(os.path.join(data_dir, 'dakota_test_Gaussian.py'), tmpdir)

    os.chdir(tmpdir)

    sweep = ips_dakota_dynamic.DakotaDynamic(
        dakota_cfg=os.path.join(tmpdir, 'dakota_test_Gaussian.in'),
        log_file=str(tmpdir.join('test.log')),
        platform_filename=os.path.join(tmpdir, 'workstation.conf'),
        debug=False,
        ips_config_template=os.path.join(tmpdir, 'dakota_test_Gaussian.ips'),
        restart_file=None,
    )
    sweep.run()

    # check dakota log
    log_file = glob.glob(str(tmpdir.join('dakota_*.log')))[0]
    with open(log_file, 'r') as f:
        lines = f.readlines()

    X = lines[-13].split()[1]

    assert float(X) == pytest.approx(0.5, rel=1e-4)

    # Check PARENT CHILD relationship
    # Get parent PORTAL_RUNID
    json_files = glob.glob(str(tmpdir.join('DAKOTA_Gaussian_TEST_1').join('simulation_log').join('*.json')))
    assert len(json_files) == 1

    with open(json_files[0], 'r') as json_file:
        lines = json_file.readlines()

    lines = [json.loads(line.strip()) for line in lines]
    assert len(lines) == 9

    # get portal_runid event
    portal_runid = lines[0]['portal_runid']
    sim_name, host, user, _ = portal_runid.rsplit('_', maxsplit=3)
    assert sim_name == 'DAKOTA_Gaussian_TEST_1'
    assert host == 'workstation'
    assert user == 'user'

    # Check child run
    json_files = glob.glob(str(tmpdir.join('DAKOTA_Gaussian_TEST_1').join('simulation_*_0000').join('simulation_log').join('*.json')))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        lines = json_file.readlines()

    lines = [json.loads(line.strip()) for line in lines]
    assert len(lines) == 8
    child_portal_runid = lines[0]['portal_runid']
    assert child_portal_runid != portal_runid

    sim_name, host, user, _ = child_portal_runid.rsplit('_', maxsplit=3)
    assert sim_name.startswith('DAKOTA_Gaussian_TEST_1')
    assert len(sim_name) > len('DAKOTA_Gaussian_TEST_1')
    assert host == 'workstation'
    assert user == 'user'

    parent_portal_runid = lines[0]['parent_portal_runid']
    assert parent_portal_runid == portal_runid


@mock.patch('ipsframework.ips_dakota_dynamic.DakotaDynamic')
def test_dakota_main(MockDakotaDynamic):
    # override sys.argv for testing
    sys.argv = ['ips_dakota_dynamic.py']
    ret = ips_dakota_dynamic.main()
    assert ret == 1
    MockDakotaDynamic.assert_not_called()

    MockDakotaDynamic.reset_mock()
    ret = ips_dakota_dynamic.main(['ips_dakota_dynamic.py'])
    assert ret == 1
    MockDakotaDynamic.assert_not_called()

    MockDakotaDynamic.reset_mock()
    sys.argv = ['ips_dakota_dynamic.py', '--somethingelse']
    ret = ips_dakota_dynamic.main()
    assert ret == 1
    MockDakotaDynamic.assert_not_called()

    MockDakotaDynamic.reset_mock()
    sys.argv = ['ips_dakota_dynamic.py', '--dakotaconfig=dakota.cfg']
    ret = ips_dakota_dynamic.main()
    assert ret == 1
    MockDakotaDynamic.assert_not_called()

    MockDakotaDynamic.reset_mock()
    sys.argv = ['ips_dakota_dynamic.py', '--simulation=sim.cfg']
    ret = ips_dakota_dynamic.main()
    assert ret == 1
    MockDakotaDynamic.assert_not_called()

    MockDakotaDynamic.reset_mock()
    sys.argv = ['ips_dakota_dynamic.py', '--simulation=sim.cfg', '--dakotaconfig=dakota.cfg']
    ret = ips_dakota_dynamic.main()
    assert ret == 0
    MockDakotaDynamic.assert_called_with('dakota.cfg', None, None, False, 'sim.cfg', None)

    MockDakotaDynamic.reset_mock()
    sys.argv = [
        'ips_dakota_dynamic.py',
        '--simulation=sim.cfg',
        '--dakotaconfig=dakota.cfg',
        '--platform=computer.conf',
        '--log=out.log',
        '--restart=dakota.rst',
        '--debug',
    ]
    ret = ips_dakota_dynamic.main()
    assert ret == 0
    MockDakotaDynamic.assert_called_with('dakota.cfg', 'out.log', 'computer.conf', True, 'sim.cfg', 'dakota.rst')
