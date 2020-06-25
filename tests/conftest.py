import pytest
import sys

from unittest.mock import patch

from jobfunnel.config.parser import parse_config
from jobfunnel.tools.tools import config_factory
from jobfunnel.__main__ import PROVIDERS
from jobfunnel.jobfunnel import MASTERLIST_HEADER

""" search_term_configs is a collection of  search_terms configurations for all supported countries. If more countries are added to JobFunnel, one may add those new configurations to this variable and those new countries/domains will be tested without having to write new tests for them, assuming of course that one uses @pytest.mark.parametrize to feed search_term_configs to those new tests."""
search_term_configs = [{'region': {'province': 'ON', 'city': 'waterloo', 'domain': 'ca', 'radius': 25}}, {
    'region': {'province': '', 'city': 'new york', 'domain': 'com', 'radius': 25}}]


@pytest.fixture()
def configure_options():
    def setup(options: list):
        """Assigns the options to argv(as if JobFunnel were called from the command line with those options)
        and calls parse_config(). This fixture assumes that the test_parse module has been tested and passes.
        """
        with patch.object(sys, 'argv', options):
            config = parse_config()
        return config

    return setup


@pytest.fixture()
def job_listings():
    def setup(attr_list: list):
        """
        This function generates job listings.
        If attr_list is empty, then it returns a single job with
        the contents of job_format, which is a default job listing defined on this fixture.
        If attr_list is not empty, it returns a job listing for each attribute pair on attr_list.
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
    def setup(attr_list: list, first_job_id: int = 0):
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
   

@pytest.fixture()
def init_scraper(configure_options):
    def setup(provider: str, options: list = ['']):
        """
        This function initializes a scraper(such as Indeed, Monster, etc) specified by provider.
        Hopefully it'll reduce some code duplication in tests.
        Args:
            provider: the provider to be inialized.
            Note that provider must match one of the keys defined for each scraper on the PROVIDERS dict on __main__.
            options: the options to be passed to the scraper, such as keywords, domain, etc.
            Note that only command-line options are accepted. Anything that needs to be tweaked that is not a command line option needs to be configured by the caller manually.
        Returns:
            An instance of the specified provider.
        """
        return PROVIDERS[provider](configure_options(options))
    return setup


@pytest.fixture()
def setup_scraper(init_scraper):
    def setup(scraper: str):
        """
        This fixture initializes the scraper state up until the point of
        having a BeautifulSoup list that can be used for scraping.
        This will help us avoid code duplication for tests.
        Args:
            scraper: The name of the scraper. Note that this name is used as a key for the PROVIDERS dict defined on __main__.py
        Returns:
            A dict of the form {'job_provider':provider,'job_list':job_soup_list, 'job_keys':job}.
            job_provider is the Indeed scraper object.
            job_soup_list is the list of BeautifulSoup objects that is ready to be scraped.
            job is a dict with all the keys from MASTERLIST_HEADER and empty values.
        """
        provider = init_scraper(scraper)
        # get the search url
        search = provider.get_search_url()
        job_soup_list = []
        provider.search_page_for_job_soups(search, 0, job_soup_list)
        job = dict([(k, '') for k in MASTERLIST_HEADER])
        return {'job_provider': provider, 'job_list': job_soup_list, 'job_keys': job}
    return setup
