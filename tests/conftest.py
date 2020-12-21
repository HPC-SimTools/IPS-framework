import pytest
import psutil
import os
from ipsframework.componentRegistry import ComponentID
from pytest_cov.embed import cleanup_on_sigterm


cleanup_on_sigterm()


@pytest.fixture(autouse=True)
def run_around_tests():
    # Reset the ComponentID.seq_num so that each test is independent
    ComponentID.seq_num = 0

    yield

    # if an assert fails then not all the children may close and the
    # test will hang, so kill all the children
    children = psutil.Process(os.getpid()).children()
    for child in children:
        child.kill()
