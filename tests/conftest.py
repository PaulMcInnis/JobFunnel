import pytest
import sys

from unittest.mock import patch

from jobfunnel.config.parser import parse_config
from jobfunnel.tools.tools import config_factory


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
        If attr_list is not empty, it returns a job listing for each attribute pair on
        attr_list.
        The expected format for each item on attr_list is
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


@pytest.fixture()
def per_id_job_listings(job_listings):
    def setup(attr_list, first_job_id=0):
        """
        This function generates job_listings in the {'job_id':{job_listing}}
        fashion. This is particularly useful for functions like tfidf_filter that expect job listings in this format.
        Args:
            attr_list: an attribute list in the [['key1', 'key2', 'keyN'], 'value'] format.
            first_job_id: At what number to start generating job ids. This is particular useful when you want different job ids but the len of attr_list is the same across multiple calls to this function.
        Returns:
            A dictionary of the format {'job_id#1':{job_listing},'job_id#2':{job_listing},
            'job_id#3':{job_listing}}. Please note that every job_id is unique.
        """
        job_list = job_listings(attr_list)
        new_job_id = first_job_id
        per_id_job_list = {}
        for job in job_list:
            job['id'] = str(new_job_id)
            per_id_job_list.update({job['id']: job})
            new_job_id += 1
        return per_id_job_list
    return setup
