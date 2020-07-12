from jobfunnel.indeed import Indeed
from jobfunnel.tools.delay import delay_alg
import pytest
from bs4 import BeautifulSoup
import re
from .conftest import search_term_configs


#test the correctness of search_tems since our tests depend on it    

def test_search_terms(init_scraper):
    indeed = init_scraper('indeed')
    assert indeed.search_terms == { 'region': {'province':'ON', 
    'city':'waterloo', 'domain':'ca', 'radius':25}, 'keywords':['Python']}
	
@pytest.mark.parametrize('search_terms_config', search_term_configs)
class TestClass():

    def test_convert_radius(self, init_scraper, search_terms_config):
        provider = init_scraper('indeed')
        provider.search_terms = search_terms_config
        assert 0 == provider.convert_radius(-1)
        assert 0 == provider.convert_radius(3)
        assert 5 == provider.convert_radius(7)
        assert 10 == provider.convert_radius(12)
        assert 15 == provider.convert_radius(20)
        assert 25 == provider.convert_radius(37)
        assert 50 == provider.convert_radius(75)
        assert 100 == provider.convert_radius(300)


    def test_get_search_url(self, init_scraper, search_terms_config):
        provider = init_scraper('indeed')
        provider.search_terms = search_terms_config
        if(provider.search_terms['region']['domain'] == 'ca'):
            assert'https://www.indeed.ca/jobs?q=Python&l=waterloo%2C+ON&radius=25&limit=50&filter=0' == provider.get_search_url()
        with pytest.raises(ValueError) as e:
            provider.get_search_url('panda')
        assert str(e.value) == 'No html method panda exists'
        with pytest.raises(NotImplementedError) as e:
            provider.get_search_url('post')


    def test_get_num_pages_to_scrape(self, init_scraper, search_terms_config):
        provider = init_scraper('indeed')
        provider.search_terms = search_terms_config
        # get the search url
        search = provider.get_search_url()

        # get the html data, initialize bs4 with lxml
        request_html = provider.s.get(search, headers=provider.headers)

        # create the soup base
        soup_base = BeautifulSoup(request_html.text, provider.bs4_parser)
        assert provider.get_num_pages_to_scrape(soup_base, max=3) <= 3


    def test_search_page_for_job_soups(self, init_scraper, search_terms_config):
        provider = init_scraper('indeed')
        provider.search_terms = search_terms_config
        # get the search url
        search = provider.get_search_url()

        # get the html data, initialize bs4 with lxml
        request_html = provider.s.get(search, headers=provider.headers)
        job_soup_list = []
        provider.search_page_for_job_soups(search, 0, job_soup_list)
        assert 0 < len(job_soup_list)


# test the process of fetching title data from a job

    def test_get_title(self, setup_scraper, search_terms_config):
        scraper = setup_scraper('indeed')
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider = scraper['job_provider']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['title'] = provider.get_title(soup)
            except AttributeError:
                continue
            if(0 < len(job['title'])):
                assert True
                return
        assert False


# test the process of fetching company data from a job

    def test_get_company(self, setup_scraper, search_terms_config):
        scraper = setup_scraper('indeed')
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider = scraper['job_provider']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['company'] = provider.get_company(soup)
            except AttributeError:
                continue
            if(0 < len(job['company'])):
                assert True
                return
        assert False


# test the process of fetching location data from a job

    def test_get_location(self, setup_scraper, search_terms_config):
        scraper = setup_scraper('indeed')
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider = scraper['job_provider']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['location'] = provider.get_location(soup)
            except AttributeError:
                continue
            if(0 < len(job['location'])):
                assert True
                return
        assert False


# test the process of fetching date data from a job

    def test_get_date(self, setup_scraper, search_terms_config):
        scraper = setup_scraper('indeed')
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider = scraper['job_provider']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['date'] = provider.get_date(soup)
            except AttributeError:
                continue
            if(0 < len(job['date'])):
                assert True
                return
        assert False

# Test the id with a strict assertion because without a job id we have 
# no job link, and without job link, we have no job to apply to
    def test_get_id(self, setup_scraper, search_terms_config):
        scraper = setup_scraper('indeed')
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider = scraper['job_provider']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['id'] = provider.get_id(soup)
            except:
                assert False
        assert True


# test the process of fetching the link to a job

    def test_get_link(self, setup_scraper, search_terms_config):
        scraper = setup_scraper('indeed')
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider = scraper['job_provider']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['id'] = provider.get_id(soup)
                job['link'] = provider.get_link(job['id'])
            except AttributeError:
                continue
            if(0 < len(job['link'])):
                assert True
                return

        assert False


# test the process of fetching the blurb from a job

    def test_get_blurb_with_delay(self, setup_scraper, search_terms_config):
        """
        Tests whether the process of fetching blurb data is working.
        """
        scraper = setup_scraper('indeed')
        provider = scraper['job_provider']
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['id'] = provider.get_id(soup)
                job['link'] = provider.get_link(job['id'])
                res_job, html = provider.get_blurb_with_delay(job, delay_alg(
                    len(job_soup_list), provider.delay_config)[0])
                provider.parse_blurb(job, html)
            except AttributeError:
                continue
            if(0 < len(job['blurb'])):
                assert True
                return

        assert False


         
    def test_search_joblink_for_blurb(self, setup_scraper, search_terms_config):
        """
        Tests whether the process of fetching blurb data is working.
        This test assumes that no delay configuration has been set.
        """
        scraper = setup_scraper('indeed')
        provider = scraper['job_provider']
        job_soup_list = scraper['job_list']
        job = scraper['job_keys']
        provider.delay_config = None
        provider.search_terms = search_terms_config
        for soup in job_soup_list:
            try:
                job['id'] = provider.get_id(soup)
                job['link'] = provider.get_link(job['id'])
                provider.search_joblink_for_blurb(job)
            except AttributeError:
                continue
            if(0 < len(job['blurb'])):
                assert True
                return

        assert False


    # Test the entire integration

    def test_scrape(self, init_scraper, mocker, 
    search_terms_config):
        # ensure that we don't scrape more than one page
        mocker.patch('jobfunnel.indeed.Indeed.get_num_pages_to_scrape', return_value=1)
        provider = init_scraper('indeed')
        provider.search_terms = search_terms_config
        provider.scrape()
