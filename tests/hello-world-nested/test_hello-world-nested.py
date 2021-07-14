from ipsframework import Framework
import os
import shutil


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

    # check results file
    sub_out = tmpdir.join("hello_example_SUPER/work/WORKERS_HELLO_HelloWorker_2/Subflow_01/simulation_results/DRIVERS_HELLOSUB_HelloDriver_5/sub_out_0.0.txt")

    assert os.path.exists(str(sub_out))
    assert os.path.islink(str(sub_out))

    with open(str(sub_out), 'r') as f:
        lines = f.readlines()

    assert lines[0] == "SUB OUTPUT FILE\n"
