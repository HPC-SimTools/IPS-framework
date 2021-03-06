import pytest
import psutil
from ipsframework.componentRegistry import ComponentID
from pytest_cov.embed import cleanup_on_sigterm


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
