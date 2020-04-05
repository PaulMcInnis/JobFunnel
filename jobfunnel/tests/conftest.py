import pytest
from unittest.mock import patch
from ..config.parser import parse_config
from ..tools.tools import config_factory
import sys


@pytest.fixture()
def configure_options():
    def setup(options):
        """Assigns the options to argv(as if JobFunnel were called from the command line with those options)
        and calls parse_config(). This fixture assumes that the test_parse module has been tested
        and passes.
        """
        with patch.object(sys, 'argv', options):
            config = parse_config()
        return config

    return setup


@pytest.fixture()
def job_listings():
    def setup(attr_list):
        """
        This function generates job listings.
        If attr_list is empty, then it returns a single job with
        the contents of job_format, which is a default job listing defined on this fixture.
        If attr_list is not empty, it returns a job listing for each  attribute pair on
        attr_list.
        The expected format for attr_list is
        [['key1', 'key2', 'keyN'], 'value']
        """
        job_format = {'status': 'new', 'title': 'Python Engineer', 'company': 'Python Corp', 'location': 'Waterloo, ON', 'date': '10 days ago', 'blurb': '', 'tags': '',
                      'link':
                      'https://job-openings.best-job-board.domain/python-engineer-waterloo-on-ca-pro'
                      'com/216808420', 'id': '216808420', 'provider': 'monster', 'query': 'Python'}
        if len(attr_list) > 0:
            return config_factory(job_format, attr_list)
        else:
            return job_format
    return setup
