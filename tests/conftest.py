import os

import pytest  # noqa=F401 - TODO: Remove this once we have tests


# TODO: This should be a fixture. For now it is not because fixtures cannot be easily called as regular functions.
def get_data_path():
    """
    Get the data path relative to this file. This is useful for when you want to test a single test file and not the
    entire test suite.
    :return:
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")
