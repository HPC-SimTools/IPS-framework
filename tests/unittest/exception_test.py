# -------------------------------------------------------------------------------
# Copyright 2006-2021 UT-Battelle, LLC. See LICENSE for more information.
# -------------------------------------------------------------------------------
import pytest
from ipsframework.ipsExceptions import BadResourceRequestException, InsufficientResourcesException


def check_BRRE():
    raise BadResourceRequestException(1234, 413, 13, 5)


def check_IRE():
    raise InsufficientResourcesException(3333, 1928717364, 2374927, 5)


def test_exception():
    with pytest.raises(BadResourceRequestException) as excinfo:
        check_BRRE()

    assert "component 1234 requested 13 nodes, which is more than possible by 5 nodes, for task 413." == str(excinfo.value)

    with pytest.raises(InsufficientResourcesException) as excinfo:
        check_IRE()

    assert "component 3333 requested 2374927 nodes, which is more than available by 5 nodes, for task 1928717364." == str(excinfo.value)
