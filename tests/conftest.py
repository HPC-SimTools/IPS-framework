import pytest
import psutil
from ipsframework.componentRegistry import ComponentID

try:
    from pytest_cov.embed import cleanup_on_sigterm
except ImportError:
    pass
else:
    cleanup_on_sigterm()


def on_terminate(proc):
    print("Process {} terminated with exit code {}".format(proc, proc.returncode))


@pytest.fixture(autouse=True)
def run_around_tests():
    # Reset the ComponentID.seq_num so that each test is independent
    ComponentID.seq_num = 0

    yield

    # if an assert fails then not all the children may close and the
    # test will hang, so kill all the children
    children = psutil.Process().children()
    for child in children:
        child.terminate()
    gone, alive = psutil.wait_procs(children, timeout=3, callback=on_terminate)
    for p in alive:
        print(f"Killing {p}")
        p.kill()


# Add a mark for test that should only run on Cori

def pytest_addoption(parser):
    parser.addoption("--runcori", action="store_true", default=False, help="run Cori tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "cori: mark test to only work on Cori")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runcori"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_cori = pytest.mark.skip(reason="need --runcori option to run")
    for item in items:
        if "cori" in item.keywords:
            item.add_marker(skip_cori)
