from ipsframework import Framework
import os
import shutil
import glob


def copy_config_and_replace(infile, srcdir, tmpdir):
    with open(os.path.join(srcdir, infile), "r") as fin:
        with open(os.path.join(tmpdir, infile), "w") as fout:
            for line in fin:
                if line.startswith("SIM_ROOT"):
                    fout.write(f"SIM_ROOT = {tmpdir}/$SIM_NAME\n")
                    IPS_ROOT = os.path.abspath(os.path.join(srcdir, '..', '..'))
                    fout.write(f"IPS_ROOT = {IPS_ROOT}\n")
                else:
                    fout.write(line)


def test_basic_serial1(tmpdir, capfd):
    datadir = os.path.dirname(__file__)
    copy_config_and_replace("basic_serial1.ips", datadir, tmpdir)
    shutil.copy(os.path.join(datadir, "platform.conf"), tmpdir)

    # setup 'input' files
    os.system(f"cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2")

    framework = Framework(config_file_list=[os.path.join(tmpdir, 'basic_serial1.ips')],
                          log_file_name=os.path.join(tmpdir, 'test.log'),
                          platform_file_name=os.path.join(tmpdir, "platform.conf"),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # Check stdout
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')

    assert captured_out[0] == "Created <class 'small_worker.small_worker'>"
    assert captured_out[1] == "Created <class 'medium_worker.medium_worker'>"
    assert captured_out[2] == "Created <class 'large_worker.large_worker'>"
    assert captured_out[3] == "small_worker : init() called"
    assert captured_out[5] == "medium_worker : init() called"
    assert captured_out[7] == "large_worker : init() called"
    assert captured_out[9] == "Current time =  3.50"
    assert captured_out[10] == "Current time =  3.60"
    assert captured_out[11] == "Current time =  3.70"

    # check files copied and created
    driver_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_serial1_0/work/drivers_testing_basic_serial1_*/*")))]
    for infile in ["file1", "ofile1", "ofile2", "sfile1", "sfile2"]:
        assert infile in driver_files

    small_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_serial1_0/work/workers_testing_small_worker_*/*")))]
    medium_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_serial1_0/work/workers_testing_medium_worker_*/*")))]
    large_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_serial1_0/work/workers_testing_large_worker_*/*")))]

    for outfile in ["my_out3.50", "my_out3.60", "my_out3.70"]:
        assert outfile in small_worker_files
        assert outfile in medium_worker_files
        assert outfile in large_worker_files

    # check sim log file
    with open(str(tmpdir.join("test_basic_serial1_0").join("test_basic_serial1_0.log")), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ["small_worker_2", "medium_worker_3", "large_worker_4"]:
        for timestamp in ["3.50", "3.60", "3.70"]:
            assert f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n' in lines


def test_basic_serial_multi(tmpdir, capfd):
    # This is the same as test_basic_serial1 except that 2 simulation files are use at the same time
    datadir = os.path.dirname(__file__)
    copy_config_and_replace("basic_serial1.ips", datadir, tmpdir)
    copy_config_and_replace("basic_serial2.ips", datadir, tmpdir)
    shutil.copy(os.path.join(datadir, "platform.conf"), tmpdir)

    # setup 'input' files
    os.system(f"cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2")

    framework = Framework(config_file_list=[os.path.join(tmpdir, 'basic_serial1.ips'),
                                            os.path.join(tmpdir, 'basic_serial2.ips')],
                          log_file_name=os.path.join(tmpdir, 'test.log'),
                          platform_file_name=os.path.join(tmpdir, "platform.conf"),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # Check stdout
    # skip checking the output because they sometimes write over the top of each other when running in parallel
    """
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')

    assert captured_out[0] == "Created <class 'small_worker.small_worker'>"
    assert captured_out[1] == "Created <class 'medium_worker.medium_worker'>"
    assert captured_out[2] == "Created <class 'large_worker.large_worker'>"
    assert captured_out[3] == "Created <class 'small_worker.small_worker'>"
    assert captured_out[4] == "Created <class 'medium_worker.medium_worker'>"
    assert captured_out[5] == "Created <class 'large_worker.large_worker'>"
    assert captured_out[7] == "small_worker : init() called"
    assert captured_out[9] == "small_worker : init() called"
    assert captured_out[11] == "medium_worker : init() called"
    assert captured_out[13] == "medium_worker : init() called"
    assert captured_out[15] == "large_worker : init() called"
    assert captured_out[17] == "large_worker : init() called"
    assert captured_out[19] == "Current time =  1.00"
    assert captured_out[20] == "Current time =  1.00"
    assert captured_out[21] == "Current time =  2.00"
    assert captured_out[22] == "Current time =  2.00"
    assert captured_out[23] == "Current time =  3.00"
    assert captured_out[24] == "Current time =  3.00"
    """

    # check files copied and created
    for no in ["1", "2"]:
        # This should also work for 2
        if no == "2":
            continue

        driver_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join(f"test_basic_serial{no}_0/work/drivers_testing_basic_serial1_*/*")))]
        for infile in ["file1", "ofile1", "ofile2", "sfile1", "sfile2"]:
            assert infile in driver_files

        small_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join(f"test_basic_serial{no}_0/work/workers_testing_small_worker_*/*")))]
        medium_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join(f"test_basic_serial{no}_0/work/workers_testing_medium_worker_*/*")))]
        large_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join(f"test_basic_serial{no}_0/work/workers_testing_large_worker_*/*")))]

        for outfile in ["my_out3.50", "my_out3.60", "my_out3.70"]:
            assert outfile in small_worker_files
            assert outfile in medium_worker_files
            assert outfile in large_worker_files

    # check basic_serial1 sim log file
    with open(str(tmpdir.join("test_basic_serial1_0").join("test_basic_serial1_0.log")), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ["small_worker_2", "medium_worker_3", "large_worker_4"]:
        for timestamp in ["3.50", "3.60", "3.70"]:
            assert f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n' in lines

    # check basic_serial2 sim log file
    with open(str(tmpdir.join("test_basic_serial2_0").join("test_basic_serial2_0.log")), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ["small_worker_6", "medium_worker_7", "large_worker_8"]:
        for timestamp in ["3.40", "3.50", "3.60"]:
            assert f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n' in lines


def test_basic_concurrent1(tmpdir, capfd):
    datadir = os.path.dirname(__file__)
    copy_config_and_replace("basic_concurrent1.ips", datadir, tmpdir)
    shutil.copy(os.path.join(datadir, "platform.conf"), tmpdir)

    # setup 'input' files
    os.system(f"cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2")

    framework = Framework(config_file_list=[os.path.join(tmpdir, 'basic_concurrent1.ips')],
                          log_file_name=os.path.join(tmpdir, 'test.log'),
                          platform_file_name=os.path.join(tmpdir, "platform.conf"),
                          debug=None,
                          verbose_debug=None,
                          cmd_nodes=0,
                          cmd_ppn=0)

    framework.run()

    # Check stdout
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')

    assert captured_out[0] == "Created <class 'small_worker.small_worker'>"
    assert captured_out[1] == "Created <class 'medium_worker.medium_worker'>"
    assert captured_out[2] == "Created <class 'large_worker.large_worker'>"
    assert captured_out[3] == "small_worker : init() called"
    assert captured_out[5] == "medium_worker : init() called"
    assert captured_out[7] == "large_worker : init() called"
    assert captured_out[9] == "Current time =  3.50"
    assert captured_out[10] == "Current time =  3.60"
    assert captured_out[11] == "Current time =  3.70"

    # check files copied and created
    driver_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_concurrent1_0/work/drivers_testing_basic_concurrent1_*/*")))]
    for infile in ["file1", "ofile1", "ofile2", "sfile1", "sfile2"]:
        assert infile in driver_files

    small_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_concurrent1_0/work/workers_testing_small_worker_*/*")))]
    medium_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_concurrent1_0/work/workers_testing_medium_worker_*/*")))]
    large_worker_files = [os.path.basename(f) for f in glob.glob(str(tmpdir.join("test_basic_concurrent1_0/work/workers_testing_large_worker_*/*")))]

    for outfile in ["my_out3.50", "my_out3.60", "my_out3.70"]:
        assert outfile in small_worker_files
        assert outfile in medium_worker_files
        assert outfile in large_worker_files

    # check sim log file
    with open(str(tmpdir.join("test_basic_concurrent1_0").join("test_basic_concurrent1_0.log")), 'r') as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ["small_worker_2", "medium_worker_3", "large_worker_4"]:
        for timestamp in ["3.50", "3.60", "3.70"]:
            assert f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n' in lines
