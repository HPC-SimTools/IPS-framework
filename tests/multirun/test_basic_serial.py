import glob
import json
import os
import shutil

import pytest

from ipsframework import Framework


def copy_config_and_replace(infile, srcdir, tmpdir):
    with open(os.path.join(srcdir, infile), 'r') as fin:
        with open(os.path.join(tmpdir, infile), 'w') as fout:
            for line in fin:
                if line.startswith('SIM_ROOT'):
                    fout.write(f'SIM_ROOT = {tmpdir}/$SIM_NAME\n')
                    ips_root = os.path.abspath(os.path.join(srcdir, '..', '..'))
                    fout.write(f'IPS_ROOT = {ips_root}\n')
                else:
                    fout.write(line)


@pytest.mark.skipif(not shutil.which('mpirun'), reason='requires mpirun')
def test_basic_serial_1(tmpdir, capfd):
    datadir = os.path.dirname(__file__)
    copy_config_and_replace('basic_serial_1.ips', datadir, tmpdir)
    shutil.copy(os.path.join(datadir, 'platform.conf'), tmpdir)

    # setup 'input' files
    os.system(f'cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2')

    framework = Framework(
        config_file_list=[os.path.join(tmpdir, 'basic_serial_1.ips')],
        log_file_name=os.path.join(tmpdir, 'test.log'),
        platform_file_name=os.path.join(tmpdir, 'platform.conf'),
        debug=False,
        verbose_debug=False,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    # Check stdout
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')
    captured_err = captured.err.split('\n')

    assert captured_err[0].startswith('Starting IPS')
    assert captured_out[0] == "Created <class 'small_worker.SmallWorker'>"
    assert captured_out[1] == "Created <class 'medium_worker.MediumWorker'>"
    assert captured_out[2] == "Created <class 'large_worker.LargeWorker'>"
    assert captured_out[3] == 'SmallWorker : init() called'
    assert captured_out[5] == 'MediumWorker : init() called'
    assert captured_out[7] == 'LargeWorker : init() called'
    assert captured_out[9] == 'Current time =  3.50'
    assert captured_out[10] == 'Current time =  3.60'
    assert captured_out[11] == 'Current time =  3.70'

    # check files copied and created
    driver_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_serial_1_0/work/drivers_testing_BasicSerial1_*/*'))
        )
    ]
    for infile in ['file1', 'ofile1', 'ofile2', 'sfile1', 'sfile2']:
        assert infile in driver_files

    small_worker_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_serial_1_0/work/workers_testing_SmallWorker_*/*'))
        )
    ]
    medium_worker_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_serial_1_0/work/workers_testing_MediumWorker_*/*'))
        )
    ]
    large_worker_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_serial_1_0/work/workers_testing_LargeWorker_*/*'))
        )
    ]

    for outfile in ['my_out3.50', 'my_out3.60', 'my_out3.70']:
        assert outfile in small_worker_files
        assert outfile in medium_worker_files
        assert outfile in large_worker_files

    # check contents of my_out files
    for outfile in ['my_out3.50', 'my_out3.60', 'my_out3.70']:
        for worker in [
            'workers_testing_SmallWorker_2',
            'workers_testing_MediumWorker_3',
        ]:
            with open(
                str(tmpdir.join('test_basic_serial_1_0/work').join(worker).join(outfile)),
                'r',
            ) as f:
                lines = f.readlines()
            assert "results = ['Rank 0 slept for 1.0 seconds']\n" in lines

        worker = 'workers_testing_LargeWorker_4'
        with open(
            str(tmpdir.join('test_basic_serial_1_0/work').join(worker).join(outfile)),
            'r',
        ) as f:
            lines = f.readlines()
        assert (
            "results = ['Rank 0 slept for 1.0 seconds', 'Rank 1 slept for 1.0 seconds']\n" in lines
        )

    # check sim log file
    with open(
        str(tmpdir.join('test_basic_serial_1_0').join('test_basic_serial_1_0.log')),
        'r',
    ) as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ['SmallWorker_2', 'MediumWorker_3', 'LargeWorker_4']:
        for timestamp in ['3.50', '3.60', '3.70']:
            assert (
                f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n'
                in lines
            )


@pytest.mark.skipif(not shutil.which('mpirun'), reason='requires mpirun')
def test_basic_serial_multi(tmpdir, capfd):
    # This is the same as test_basic_serial_1 except that 2 simulation files are use at the same time
    datadir = os.path.dirname(__file__)
    copy_config_and_replace('basic_serial_1.ips', datadir, tmpdir)
    copy_config_and_replace('basic_serial_2.ips', datadir, tmpdir)
    shutil.copy(os.path.join(datadir, 'platform.conf'), tmpdir)

    # setup 'input' files
    os.system(f'cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2')

    framework = Framework(
        config_file_list=[
            os.path.join(tmpdir, 'basic_serial_1.ips'),
            os.path.join(tmpdir, 'basic_serial_2.ips'),
        ],
        log_file_name=os.path.join(tmpdir, 'test.log'),
        platform_file_name=os.path.join(tmpdir, 'platform.conf'),
        debug=False,
        verbose_debug=False,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    # Check stdout
    # skip checking the output because they sometimes write over the top of each other when running in parallel
    """
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')

    assert captured_out[0] == "Created <class 'small_worker.SmallWorker'>"
    assert captured_out[1] == "Created <class 'medium_worker.MediumWorker'>"
    assert captured_out[2] == "Created <class 'large_worker.LargeWorker'>"
    assert captured_out[3] == "Created <class 'small_worker.SmallWorker'>"
    assert captured_out[4] == "Created <class 'medium_worker.MediumWorker'>"
    assert captured_out[5] == "Created <class 'large_worker.LargeWorker'>"
    assert captured_out[7] == "SmallWorker : init() called"
    assert captured_out[9] == "SmallWorker : init() called"
    assert captured_out[11] == "MediumWorker : init() called"
    assert captured_out[13] == "MediumWorker : init() called"
    assert captured_out[15] == "LargeWorker : init() called"
    assert captured_out[17] == "LargeWorker : init() called"
    assert captured_out[19] == "Current time =  1.00"
    assert captured_out[20] == "Current time =  1.00"
    assert captured_out[21] == "Current time =  2.00"
    assert captured_out[22] == "Current time =  2.00"
    assert captured_out[23] == "Current time =  3.00"
    assert captured_out[24] == "Current time =  3.00"
    """

    # check files copied and created
    for no in ['1', '2']:
        driver_files = [
            os.path.basename(f)
            for f in glob.glob(
                str(tmpdir.join(f'test_basic_serial_{no}_0/work/drivers_testing_BasicSerial*_*/*'))
            )
        ]
        for infile in ['file1', 'ofile1', 'ofile2', 'sfile1', 'sfile2']:
            assert infile in driver_files

        small_worker_files = [
            os.path.basename(f)
            for f in glob.glob(
                str(tmpdir.join(f'test_basic_serial_{no}_0/work/workers_testing_SmallWorker_*/*'))
            )
        ]
        medium_worker_files = [
            os.path.basename(f)
            for f in glob.glob(
                str(tmpdir.join(f'test_basic_serial_{no}_0/work/workers_testing_MediumWorker_*/*'))
            )
        ]
        large_worker_files = [
            os.path.basename(f)
            for f in glob.glob(
                str(tmpdir.join(f'test_basic_serial_{no}_0/work/workers_testing_LargeWorker_*/*'))
            )
        ]

        if no == '1':
            for outfile in ['my_out3.50', 'my_out3.60', 'my_out3.70']:
                assert outfile in small_worker_files
                assert outfile in medium_worker_files
                assert outfile in large_worker_files
        else:
            for outfile in ['my_out3.40', 'my_out3.50', 'my_out3.60']:
                assert outfile in small_worker_files
                assert outfile in medium_worker_files
                assert outfile in large_worker_files

    # check contents of my_out files
    for outfile in ['my_out3.50', 'my_out3.60', 'my_out3.70']:
        for worker in [
            'workers_testing_SmallWorker_2',
            'workers_testing_MediumWorker_3',
        ]:
            with open(
                str(tmpdir.join('test_basic_serial_1_0/work').join(worker).join(outfile)),
                'r',
            ) as f:
                lines = f.readlines()
            assert "results = ['Rank 0 slept for 1.0 seconds']\n" in lines

        worker = 'workers_testing_LargeWorker_4'
        with open(
            str(tmpdir.join('test_basic_serial_1_0/work').join(worker).join(outfile)),
            'r',
        ) as f:
            lines = f.readlines()
        assert (
            "results = ['Rank 0 slept for 1.0 seconds', 'Rank 1 slept for 1.0 seconds']\n" in lines
        )

    for outfile in ['my_out3.40', 'my_out3.50', 'my_out3.60']:
        for worker in [
            'workers_testing_SmallWorker_6',
            'workers_testing_MediumWorker_7',
        ]:
            with open(
                str(tmpdir.join('test_basic_serial_2_0/work').join(worker).join(outfile)),
                'r',
            ) as f:
                lines = f.readlines()
            assert "results = ['Rank 0 slept for 1.0 seconds']\n" in lines

        worker = 'workers_testing_LargeWorker_8'
        with open(
            str(tmpdir.join('test_basic_serial_2_0/work').join(worker).join(outfile)),
            'r',
        ) as f:
            lines = f.readlines()
        assert (
            "results = ['Rank 0 slept for 1.0 seconds', 'Rank 1 slept for 1.0 seconds']\n" in lines
        )

    # check basic_serial_1 sim log file
    with open(
        str(tmpdir.join('test_basic_serial_1_0').join('test_basic_serial_1_0.log')),
        'r',
    ) as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ['SmallWorker_2', 'MediumWorker_3', 'LargeWorker_4']:
        for timestamp in ['3.50', '3.60', '3.70']:
            assert (
                f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n'
                in lines
            )

    # check basic_serial_2 sim log file
    with open(
        str(tmpdir.join('test_basic_serial_2_0').join('test_basic_serial_2_0.log')),
        'r',
    ) as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ['SmallWorker_6', 'MediumWorker_7', 'LargeWorker_8']:
        for timestamp in ['3.40', '3.50', '3.60']:
            assert (
                f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n'
                in lines
            )

    # check that the parent_portal_runid is correctly set
    serial1_json_files = glob.glob(
        str(tmpdir.join('test_basic_serial_1_0').join('simulation_log').join('*.jsonl'))
    )
    assert len(serial1_json_files) == 1
    with open(serial1_json_files[0], 'r') as json_file:
        serial1_lines = json_file.readlines()

    serial1_ips_start = json.loads(serial1_lines[0])
    assert serial1_ips_start['parent_portal_runid'] is None
    serial1_portal_runid = serial1_ips_start['portal_runid']

    serial2_json_files = glob.glob(
        str(tmpdir.join('test_basic_serial_2_0').join('simulation_log').join('*.jsonl'))
    )
    assert len(serial2_json_files) == 1
    with open(serial2_json_files[0], 'r') as json_file:
        serial2_lines = json_file.readlines()

    serial2_ips_start = json.loads(serial2_lines[0])
    assert serial2_ips_start['parent_portal_runid'] == serial1_portal_runid
    assert serial2_ips_start['portal_runid'] is not None
    assert serial2_ips_start['portal_runid'] != serial1_portal_runid


@pytest.mark.skipif(not shutil.which('mpirun'), reason='requires mpirun')
def test_basic_concurrent_1(tmpdir, capfd):
    datadir = os.path.dirname(__file__)
    copy_config_and_replace('basic_concurrent_1.ips', datadir, tmpdir)
    shutil.copy(os.path.join(datadir, 'platform.conf'), tmpdir)

    # setup 'input' files
    os.system(f'cd {tmpdir}; touch file1 ofile1 ofile2 sfile1 sfile2')

    framework = Framework(
        config_file_list=[os.path.join(tmpdir, 'basic_concurrent_1.ips')],
        log_file_name=os.path.join(tmpdir, 'test.log'),
        platform_file_name=os.path.join(tmpdir, 'platform.conf'),
        debug=None,
        verbose_debug=None,
        cmd_nodes=0,
        cmd_ppn=0,
    )

    framework.run()

    # Check stdout
    captured = capfd.readouterr()
    captured_out = captured.out.split('\n')
    captured_err = captured.err.split('\n')

    assert captured_err[0].startswith('Starting IPS')
    assert captured_out[0] == "Created <class 'small_worker.SmallWorker'>"
    assert captured_out[1] == "Created <class 'medium_worker.MediumWorker'>"
    assert captured_out[2] == "Created <class 'large_worker.LargeWorker'>"
    assert captured_out[3] == 'SmallWorker : init() called'
    assert captured_out[5] == 'MediumWorker : init() called'
    assert captured_out[7] == 'LargeWorker : init() called'
    assert captured_out[9] == 'Current time =  3.50'
    assert captured_out[10] == 'nonblocking wait_call() invoked before call 12 finished'
    assert captured_out[11] == 'Current time =  3.60'
    assert captured_out[12] == 'nonblocking wait_call() invoked before call 15 finished'
    assert captured_out[13] == 'Current time =  3.70'
    assert captured_out[14] == 'nonblocking wait_call() invoked before call 18 finished'

    # check files copied and created
    driver_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_concurrent_1_0/work/drivers_testing_BasicConcurrent1_*/*'))
        )
    ]
    for infile in ['file1', 'ofile1', 'ofile2', 'sfile1', 'sfile2']:
        assert infile in driver_files

    small_worker_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_concurrent_1_0/work/workers_testing_SmallWorker_*/*'))
        )
    ]
    medium_worker_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_concurrent_1_0/work/workers_testing_MediumWorker_*/*'))
        )
    ]
    large_worker_files = [
        os.path.basename(f)
        for f in glob.glob(
            str(tmpdir.join('test_basic_concurrent_1_0/work/workers_testing_LargeWorker_*/*'))
        )
    ]

    for outfile in ['my_out3.50', 'my_out3.60', 'my_out3.70']:
        assert outfile in small_worker_files
        assert outfile in medium_worker_files
        assert outfile in large_worker_files

    # check contents of my_out files
    for outfile in ['my_out3.50', 'my_out3.60', 'my_out3.70']:
        for worker in [
            'workers_testing_SmallWorker_2',
            'workers_testing_MediumWorker_3',
        ]:
            with open(
                str(tmpdir.join('test_basic_concurrent_1_0/work').join(worker).join(outfile)),
                'r',
            ) as f:
                lines = f.readlines()
            assert "results = ['Rank 0 slept for 1.0 seconds']\n" in lines

        worker = 'workers_testing_LargeWorker_4'
        with open(
            str(tmpdir.join('test_basic_concurrent_1_0/work').join(worker).join(outfile)),
            'r',
        ) as f:
            lines = f.readlines()
        assert (
            "results = ['Rank 0 slept for 1.0 seconds', 'Rank 1 slept for 1.0 seconds']\n" in lines
        )

    # check sim log file
    with open(
        str(tmpdir.join('test_basic_concurrent_1_0').join('test_basic_concurrent_1_0.log')),
        'r',
    ) as f:
        lines = f.readlines()

    # remove timestamp
    lines = [line[24:] for line in lines]

    for worker in ['SmallWorker_2', 'MediumWorker_3', 'LargeWorker_4']:
        for timestamp in ['3.50', '3.60', '3.70']:
            assert (
                f'workers_testing_{worker} INFO     Stepping Worker timestamp={timestamp}\n'
                in lines
            )
