from ipsframework.ips_dakota_dynamic import DakotaDynamic
import os
import shutil
import pytest
import glob


def copy_config_and_replace(infile, outfile, tmpdir):
    with open(infile, "r") as fin:
        with open(outfile, "w") as fout:
            for line in fin:
                if "SCRIPT" in line:
                    fout.write(line.replace("$PWD", str(tmpdir)))
                elif line.startswith("SIM_ROOT"):
                    fout.write(f"SIM_ROOT = {tmpdir}/$SIM_NAME\n")
                else:
                    fout.write(line)


@pytest.mark.skipif(shutil.which('dakota') is None,
                    reason="Requires dakota to run this test")
def test_dakota(tmpdir):
    data_dir = os.path.dirname(__file__)
    copy_config_and_replace(os.path.join(data_dir, "dakota_test_Rosenbrock.ips"), tmpdir.join("dakota_test_Rosenbrock.ips"), tmpdir)
    shutil.copy(os.path.join(data_dir, "workstation.conf"), tmpdir)
    shutil.copy(os.path.join(data_dir, "dakota_test_Rosenbrock.in"), tmpdir)
    shutil.copy(os.path.join(data_dir, "dakota_test_Rosenbrock.py"), tmpdir)

    os.chdir(tmpdir)

    sweep = DakotaDynamic(dakota_cfg=os.path.join(tmpdir, "dakota_test_Rosenbrock.in"),
                          log_file=str(tmpdir.join('test.log')),
                          platform_filename=os.path.join(tmpdir, "workstation.conf"),
                          debug=False,
                          ips_config_template=os.path.join(tmpdir, "dakota_test_Rosenbrock.ips"),
                          restart_file=None)
    sweep.run()

    # check dakota log
    log_file = glob.glob(str(tmpdir.join("dakota_*.log")))[0]
    with open(log_file, 'r') as f:
        lines = f.readlines()

    X1, X2 = lines[-22].split()[1:]

    assert float(X1) == pytest.approx(1, rel=1e-3)
    assert float(X2) == pytest.approx(1, rel=1e-3)
