from ipsframework.resourceHelper import getResourceList
from ipsframework.ipsExceptions import InvalidResourceSettingsException
import pytest
from unittest import mock


# checkjob

@mock.patch('subprocess.Popen')
def test_resourceHelper_checkjob(subprocess_popen_mock, monkeypatch):
    # mock the subprocess.Popen().returncode attribute and subprocess.Popen().stdout.readlines()
    type(subprocess_popen_mock.return_value).returncode = mock.PropertyMock(return_value=0)
    readlines = mock.Mock()
    output = """
    Total Requested Tasks: 8

    Allocated Nodes:
    [n27:1][n10:4]
    """
    readlines.readlines.return_value = output.split('\n')
    type(subprocess_popen_mock.return_value).stdout = readlines

    # create mock services and get_platform_parameter return values
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODE_DETECTION': "checkjob"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    # set mock return values
    monkeypatch.setenv("PBS_JOBID", "1234")

    # get resources from mock slurm env
    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert ['n27', '1'] in listOfNodes
    assert ['n10', '4'] in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 4
    assert not accurateNodes


# qstat

@mock.patch('subprocess.Popen')
def test_resourceHelper_qstat(subprocess_popen_mock, monkeypatch):
    # mock the subprocess.Popen().returncode attribute and subprocess.Popen().stdout.readlines()
    type(subprocess_popen_mock.return_value).returncode = mock.PropertyMock(return_value=0)
    readlines = mock.Mock()
    readlines.readlines.return_value = [' Resource_List.mppwidth = 64 ',
                                        ' Resource_List.mppnppn = 2   ']
    type(subprocess_popen_mock.return_value).stdout = readlines

    # create mock services and get_platform_parameter return values
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODE_DETECTION': "qstat"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    # try with missing environment variables
    with pytest.raises(KeyError) as excinfo:
        getResourceList(services, 'host')
    assert "'PBS_JOBID'" == str(excinfo.value)

    # set mock return values
    monkeypatch.setenv("PBS_JOBID", "1234")

    # get resources from mock slurm env
    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 0
    assert cpn == 8
    assert spn == 1
    assert ppn == 2
    assert not accurateNodes

    # now for HOST=stix
    readlines.readlines.return_value = ['  exec_host = compute1+compute2 ',
                                        '  Resource_List.nodect = 2      ',
                                        '  Resource_List.nodes = 2:ppn=2 ']
    monkeypatch.setenv("HOST", "stix")

    # get resources from mock slurm env
    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert 'compute1' in listOfNodes
    assert 'compute2' in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 2
    assert not accurateNodes


# qstat2

@mock.patch('subprocess.Popen')
def test_resourceHelper_qstat2(subprocess_popen_mock, monkeypatch):
    # mock the subprocess.Popen().returncode attribute and subprocess.Popen().stdout.readlines()
    type(subprocess_popen_mock.return_value).returncode = mock.PropertyMock(return_value=0)
    readlines = mock.Mock()
    readlines.readlines.return_value = [' exec_host = compute1/1+compute1/0+compute2/2+compute2/0 ',
                                        ' Hold_Types = n   ']
    type(subprocess_popen_mock.return_value).stdout = readlines

    # create mock services and get_platform_parameter return values
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODE_DETECTION': "qstat2"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    # try with missing environment variables
    with pytest.raises(KeyError) as excinfo:
        getResourceList(services, 'host')
    assert "'PBS_JOBID'" == str(excinfo.value)

    # set mock return values
    monkeypatch.setenv("PBS_JOBID", "1234")

    # get resources from mock slurm env
    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert ('compute1', ['1', '0']) in listOfNodes
    assert ('compute2', ['2', '0']) in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 2
    assert accurateNodes


# pbs_env

def test_resourceHelper_pbs_env(monkeypatch, tmpdir):
    # create nodefile
    p = tmpdir.join("nodefile")
    p.write("compute0\ncompute1\n")

    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODE_DETECTION': "pbs_env"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    # try with missing environment variables
    with pytest.raises(KeyError) as excinfo:
        getResourceList(services, 'host')
    assert "'PBS_NNODES'" == str(excinfo.value)

    # PBS_NNODES
    monkeypatch.setenv("PBS_NNODES", "2")

    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert ('dummynode0', 1) in listOfNodes
    assert ('dummynode1', 1) in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 1
    assert not accurateNodes

    # PBS_NODEFILE
    monkeypatch.setenv("PBS_NODEFILE", str(p))

    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert ('compute0', 1) in listOfNodes
    assert ('compute1', 1) in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 1
    assert accurateNodes


# slurm_env

@mock.patch('subprocess.check_output')
def test_resourceHelper_slurm_env(subprocess_check_output_mock, monkeypatch):
    subprocess_check_output_mock.return_value = "nid00658\nnid00659\n"

    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODE_DETECTION': "slurm_env"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    # try with missing environment variables
    with pytest.raises(KeyError) as excinfo:
        getResourceList(services, 'host')
    assert "'SLURM_NODELIST'" == str(excinfo.value)

    # set mock return values
    monkeypatch.setenv("SLURM_NODELIST", "nid00[658-659]")

    # try with missing environment variables
    with pytest.raises(KeyError) as excinfo:
        getResourceList(services, 'host')
    assert "'SLURM_JOB_TASKS_PER_NODE'" == str(excinfo.value)

    monkeypatch.setenv("SLURM_TASKS_PER_NODE", "2(x2)")

    # get resources from mock slurm env
    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert ('nid00658', 2) in listOfNodes
    assert ('nid00659', 2) in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 2
    assert accurateNodes


# manual

def test_resourceHelper_manual():
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODES': 2,
                  'PROCS_PER_NODE': 2,
                  'TOTAL_PROCS': 0,
                  'NODE_DETECTION': "manual"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 2
    assert ('dummynode0', 2) in listOfNodes
    assert ('dummynode1', 2) in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 2
    assert not accurateNodes


def test_resourceHelper_manual_InvalidException():
    # SOCKETS_PER_NODE > CORES_PER_NODE
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 16,
                  'NODES': 2,
                  'PROCS_PER_NODE': 2,
                  'TOTAL_PROCS': 0,
                  'NODE_DETECTION': "manual"}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    with pytest.raises(InvalidResourceSettingsException) as excinfo:
        getResourceList(services, 'host')
    assert ("Invalid resource specification in platform configuration file:  socket per node count (16) greater than core per node count (8)."
            == str(excinfo.value))

    # CORES_PER_NODE % SOCKETS_PER_NODE != 0
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 3,
                  'NODES': 2,
                  'PROCS_PER_NODE': 2,
                  'TOTAL_PROCS': 0,
                  'NODE_DETECTION': "manual"}
        return params[param]

    services.get_platform_parameter.side_effect = get_param

    with pytest.raises(InvalidResourceSettingsException) as excinfo:
        getResourceList(services, 'host')
    assert ("Invalid resource specification in platform configuration file:  socket per node count (3) not divisible by core per node count (8)."
            == str(excinfo.value))


# with no detection defined

def test_resourceHelper_no_detection():
    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODE_DETECTION': ""}
        return params[param]

    # create mock services and get_platform_parameter return values
    services = mock.Mock()
    services.get_platform_parameter.side_effect = get_param

    with pytest.raises(KeyError) as excinfo:
        getResourceList(services, 'host')
    assert "'NODES'" == str(excinfo.value)

    # fallback to manual is enough info supplied

    def get_param(param, silent=True):
        params = {'CORES_PER_NODE': 8,
                  'SOCKETS_PER_NODE': 1,
                  'NODES': 0,
                  'PROCS_PER_NODE': 0,
                  'TOTAL_PROCS': 0,
                  'NODE_DETECTION': ""}
        return params[param]

    services.get_platform_parameter.side_effect = get_param

    listOfNodes, cpn, spn, ppn, accurateNodes = getResourceList(services, 'host')

    assert len(listOfNodes) == 1
    assert ('dummynode0', 8) in listOfNodes
    assert cpn == 8
    assert spn == 1
    assert ppn == 8
    assert not accurateNodes
