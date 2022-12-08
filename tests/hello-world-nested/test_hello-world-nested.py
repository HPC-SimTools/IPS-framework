import os
import shutil
import json
import glob
from ipsframework import Framework


def copy_config_and_replace(infile, outfile, tmpdir):
    with open(infile, "r") as fin:
        with open(outfile, "w") as fout:
            for line in fin:
                if line.startswith("TEST_ROOT"):
                    fout.write(f"TEST_ROOT = {tmpdir}\n")
                elif line.startswith("LOG_FILE"):
                    fout.write(line.replace("LOG_FILE = ", f"LOG_FILE = {tmpdir}/"))
                else:
                    fout.write(line)


def test_hello_world_nested(tmpdir, capfd):
    data_dir = os.path.dirname(__file__)
    copy_config_and_replace(os.path.join(data_dir, "hello_world.config"), tmpdir.join("hello_world.config"), tmpdir)
    copy_config_and_replace(os.path.join(data_dir, "hello_world_sub.config"), tmpdir.join("hello_world_sub.config"), tmpdir)
    shutil.copy(os.path.join(data_dir, "workstation.conf"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_driver.py"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_worker.py"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_driver_sub.py"), tmpdir)
    shutil.copy(os.path.join(data_dir, "hello_worker_sub.py"), tmpdir)
    with open(tmpdir.join('input.txt'), 'w') as f:
        f.write("INPUT FILE\n")

    framework = Framework(config_file_list=[os.path.join(tmpdir, "hello_world.config")],
                          log_file_name=str(tmpdir.join('test.log')),
                          platform_file_name=os.path.join(tmpdir, "workstation.conf"),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    captured = capfd.readouterr()

    captured_out = captured.out.split('\n')
    assert captured_out[0].startswith("Starting IPS")
    assert captured_out[1] == "Created <class 'hello_driver.HelloDriver'>"
    assert captured_out[2] == "Created <class 'hello_worker.HelloWorker'>"
    assert captured_out[3] == "Hello from HelloWorker - new1"
    assert captured_out[4] == "Created <class 'hello_driver_sub.HelloDriver'>"
    assert captured_out[5] == "Created <class 'hello_worker_sub.HelloWorker'>"
    assert captured_out[6] == "Hello from HelloWorker - sub"
    assert captured_out[7] == "made it out of the worker call"
    assert captured.err == ''

    # check sim log file
    with open(str(tmpdir.join("Hello_world_sim.log")), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    assert 'WORKERSSUB_HELLO_HelloWorker_6 INFO     Hello from HelloWorker - sub\n' in lines

    # check sub workflow results file
    sub_out = tmpdir.join("hello_example_SUPER/work/WORKERS_HELLO_HelloWorker_2/Subflow_01/simulation_results/DRIVERS_HELLOSUB_HelloDriver_5/sub_out_0.0.txt")

    assert os.path.exists(str(sub_out))
    assert os.path.islink(str(sub_out))

    with open(str(sub_out), 'r') as f:
        lines = f.readlines()

    assert lines[0] == "SUB OUTPUT FILE\n"

    # check results file in parent workflow
    sub_out = tmpdir.join("hello_example_SUPER/work/WORKERS_HELLO_HelloWorker_2/sub_out.txt")

    assert os.path.exists(str(sub_out))

    with open(str(sub_out), 'r') as f:
        lines = f.readlines()

    assert lines[0] == "SUB OUTPUT FILE\n"

    # check input file staging
    sub_input = tmpdir.join("hello_example_SUPER/work/WORKERS_HELLO_HelloWorker_2/input.txt")

    assert os.path.exists(str(sub_input))

    with open(str(sub_input), 'r') as f:
        lines = f.readlines()

    assert lines[0] == "SUB INPUT FILE\n"

    sub_input = tmpdir.join("hello_example_SUPER/work/WORKERS_HELLO_HelloWorker_2/HELLO_DRIVER/input.txt")

    assert os.path.exists(str(sub_input))

    with open(str(sub_input), 'r') as f:
        lines = f.readlines()

    assert lines[0] == "SUB INPUT FILE\n"

    # check the simulation log json
    json_files = glob.glob(str(tmpdir.join("hello_example_SUPER").join("simulation_log").join("*.json")))
    assert len(json_files) == 1
    with open(json_files[0], 'r') as json_file:
        events = [json.loads(event) for event in json_file.readlines()]

    assert len(events) == 25
    assert events[-1]['eventtype'] == "IPS_END"

    codes = set(event["code"] for event in events)

    # Check that the sub wortflow writes to the same json file
    assert len(codes) == 5
    assert "Framework" in codes
    assert "DRIVERS_HELLO_HelloDriver" in codes
    assert "WORKERS_HELLO_HelloWorker" in codes
    assert "DRIVERS_HELLOSUB_HelloDriver" in codes
    assert "WORKERSSUB_HELLO_HelloWorker" in codes

    # Check that phystimestamp get updated by the sub workflow
    assert events[0]["phystimestamp"] == -1
    assert events[-1]["phystimestamp"] == 1
