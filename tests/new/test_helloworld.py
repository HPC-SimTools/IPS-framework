from ipsframework.ips import Framework
import os
import shutil
import psutil
import pytest
import json


@pytest.fixture(autouse=True)
def run_around_tests():
    yield
    # if an assert fails then not all the children may close and the
    # test will hang, so kill all the children
    children = psutil.Process(os.getpid()).children()
    for child in children:
        child.kill()


def copy_config_and_replace(infile, outfile, tmpdir, task_pool=False):
    with open(infile, "r") as fin:
        with open(outfile, "w") as fout:
            for line in fin:
                if "hello_driver.py" in line or "hello_worker.py" in line:
                    if task_pool:
                        fout.write(line.replace("${BIN_PATH}", str(tmpdir)).replace("hello_worker.py", "hello_worker_task_pool.py"))
                    else:
                        fout.write(line.replace("${BIN_PATH}", str(tmpdir)))
                elif "BIN_PATH" in line:
                    fout.write(line.replace("${IPS_ROOT}/tests/helloworld", ""))
                elif line.startswith("SIM_ROOT"):
                    fout.write(f"SIM_ROOT = {tmpdir}\n")
                elif line.startswith("LOG_FILE"):
                    fout.write(line.replace("LOG_FILE = ", f"LOG_FILE = {tmpdir}/"))
                else:
                    fout.write(line)


def test_helloworld(tmpdir, capfd):
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'helloworld')
    copy_config_and_replace(os.path.join(data_dir, "hello_world.ips"), tmpdir.join("hello_world.ips"), tmpdir)
    shutil.copy(os.path.join(data_dir, "platform.conf"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_driver.py"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_worker.py"), tmpdir)

    framework = Framework(do_create_runspace=True,  # create runspace: init.init()
                          do_run_setup=True,        # validate inputs: sim_comps.init()
                          do_run=True,              # Main part of simulation
                          config_file_list=[os.path.join(tmpdir, "hello_world.ips")],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=os.path.join(tmpdir, "platform.conf"),
                          compset_list=[],
                          debug=None,
                          ftb=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    assert framework.ips_dosteps['CREATE_RUNSPACE']
    assert framework.ips_dosteps['RUN_SETUP']
    assert framework.ips_dosteps['RUN']

    assert framework.log_file_name.endswith('test.log')

    assert len(framework.config_manager.get_framework_components()) == 1

    component_map = framework.config_manager.get_component_map()

    assert len(component_map) == 1
    assert 'Hello_world_1' in component_map
    hello_world_1 = component_map['Hello_world_1']
    assert len(hello_world_1) == 1
    assert hello_world_1[0].get_class_name() == 'HelloDriver'
    assert hello_world_1[0].get_instance_name().startswith('Hello_world_1@HelloDriver')
    # assert hello_world_1[0].get_seq_num() == 1 # need to find a way to reset static variable
    assert hello_world_1[0].get_serialization().startswith('Hello_world_1@HelloDriver')
    assert hello_world_1[0].get_sim_name() == 'Hello_world_1'

    framework.run()

    captured = capfd.readouterr()

    captured_out = captured.out.split('\n')
    assert captured_out[0] == "Created <class 'hello_driver.HelloDriver'>"
    assert captured_out[1] == "Created <class 'hello_worker.HelloWorker'>"
    assert captured_out[2].endswith('checklist.conf" could not be found, continuing without.')
    assert captured_out[3] == 'HelloDriver: init'
    assert captured_out[4] == 'HelloDriver: finished worker init call'
    assert captured_out[5] == 'HelloDriver: beginning step call'
    assert captured_out[6] == 'Hello from HelloWorker'
    assert captured_out[7] == 'HelloDriver: finished worker call'
    assert captured.err == ''

    # cleanup
    for fname in ["test_helloworld0.zip", "dask_preload.py"]:
        if os.path.isfile(fname):
            os.remove(fname)


def test_helloworld_task_pool(tmpdir, capfd):
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'helloworld')
    copy_config_and_replace(os.path.join(data_dir, "hello_world.ips"), tmpdir.join("hello_world.ips"), tmpdir, task_pool=True)
    shutil.copy(os.path.join(data_dir, "platform.conf"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_driver.py"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_worker_task_pool.py"), tmpdir)

    framework = Framework(do_create_runspace=True,  # create runspace: init.init()
                          do_run_setup=True,        # validate inputs: sim_comps.init()
                          do_run=True,              # Main part of simulation
                          config_file_list=[os.path.join(tmpdir, "hello_world.ips")],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=os.path.join(tmpdir, "platform.conf"),
                          compset_list=[],
                          debug=None,
                          ftb=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    assert framework.ips_dosteps['CREATE_RUNSPACE']
    assert framework.ips_dosteps['RUN_SETUP']
    assert framework.ips_dosteps['RUN']

    assert framework.log_file_name.endswith('test.log')

    assert len(framework.config_manager.get_framework_components()) == 1

    component_map = framework.config_manager.get_component_map()

    assert len(component_map) == 1
    assert 'Hello_world_1' in component_map
    hello_world_1 = component_map['Hello_world_1']
    assert len(hello_world_1) == 1
    assert hello_world_1[0].get_class_name() == 'HelloDriver'
    assert hello_world_1[0].get_instance_name().startswith('Hello_world_1@HelloDriver')
    # assert hello_world_1[0].get_seq_num() == 1 # need to find a way to reset static variable
    assert hello_world_1[0].get_serialization().startswith('Hello_world_1@HelloDriver')
    assert hello_world_1[0].get_sim_name() == 'Hello_world_1'

    framework.run()

    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')

    assert captured_out[0] == "Created <class 'hello_driver.HelloDriver'>"
    assert captured_out[1] == "Created <class 'hello_worker_task_pool.HelloWorker'>"
    assert captured_out[2].endswith('checklist.conf" could not be found, continuing without.')
    assert captured_out[3] == 'HelloDriver: init'
    assert captured_out[4] == 'HelloDriver: finished worker init call'
    assert captured_out[5] == 'HelloDriver: beginning step call'
    assert captured_out[6] == 'Hello from HelloWorker'
    assert captured_out[7] == 'ret_val =  10'

    exit_status = json.loads(captured_out[8].replace("'", '"'))
    assert len(exit_status) == 10
    for n in range(10):
        assert f'task_{n}' in exit_status
        assert exit_status[f'task_{n}'] == 0

    assert captured_out[9] == "====== Non Blocking "

    for line in range(10, len(captured_out) - 2):
        if "Nonblock_task" in captured_out[line]:
            assert captured_out[line].endswith("': 0}")

    assert captured_out[-3] == 'Active =  0 Finished =  10'
    assert captured_out[-2] == 'HelloDriver: finished worker call'
    assert captured.err == ''

    # cleanup
    for fname in ["test_helloworld_task_pool0.zip", "dask_preload.py"]:
        if os.path.isfile(fname):
            os.remove(fname)
