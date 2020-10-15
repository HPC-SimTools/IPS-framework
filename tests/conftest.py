import pytest
import psutil
import os


@pytest.fixture(autouse=True)
def run_around_tests():
    yield
    # if an assert fails then not all the children may close and the
    # test will hang, so kill all the children
    children = psutil.Process(os.getpid()).children()
    for child in children:
        child.kill()
