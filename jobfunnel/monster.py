import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging import info as log_info
from math import ceil
from requests import get
from time import sleep

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age
from .tools.delay import random_delay


class Monster(JobFunnel):

    def __init__(self, args):
        super().__init__(args)
        self.provider = 'monster'
        self.max_results_per_page = 25
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.monster.{0}/'.format(
                self.search_terms['region']['domain']),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def search_monster_joblink_for_blurb(self, job):
        """function that scrapes the monster job link for the blurb"""
        search = job['link']
        log_info('getting monster search: {}'.format(search))
        request_HTML = get(search, headers=self.headers)
        job_link_soup = BeautifulSoup(
            request_HTML.text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescription').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    # Split apart above function into two so gotten blurbs can be parsed while
    # while others blurbs are being obtained.
    def get_blurb_ms_w_dly(self, job, delay):
        """
        function that gets blurb from monster and uses request delaying
        """
        sleep(delay)
        search = job['link']
        log_info('getting glassdoor search: {}'.format(search))
        res = get(search, headers=self.headers).text
        return job, res

    def parse_blurb_ms(self, job, html):
        """
        stores parsed job description into job dict
        """
        job_link_soup = BeautifulSoup(
            html, self.bs4_parser)
        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescription').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def scrape(self):
        """function that scrapes job posting from monster and pickles it"""
        log_info(
            'jobfunnel monster to pickle running @ : ' + self.date_string)
        # ID regex quantifiers
        id_regex = \
            re.compile(
                r'/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab]['
                r'0-9a-f]{3}-[0-9a-f]{12})|\d+)')

        # form the query string
        query = '-'.join(self.search_terms['keywords'])

        # build the job search URL
        search = 'https://www.monster.{0}/jobs/search/?q={1}&where={2}__2C-{' \
                 '3}' \
                 '&intcid=skr_navigation_nhpso_searchMain&rad={4}&where={' \
                 '2}__' \
                 '2c-{3}'.format(
            self.search_terms['region']['domain'],
            query,
            self.search_terms['region']['city'],
            self.search_terms['region']['province'],
            self.search_terms['region']['radius'])

        # get the HTML data, initialize bs4 with lxml
        request_HTML = get(search, headers=self.headers)
        soup_base = BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find('h2', 'figure').text.strip()
        num_results = int(re.findall(r'(\d+)', num_results)[0])
        log_info(
            'Found {} monster results for query={}'.format(num_results, query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / self.max_results_per_page))
        page_url = '{0}&start={1}'.format(search, pages)
        log_info(
            'getting monster pages 1 to {0} : {1}'.format(pages, page_url))
        jobs = BeautifulSoup(
            get(page_url, headers=self.headers).text,
            self.bs4_parser).find_all('div', attrs={'class': 'flex-row'})

        list_of_job_soups.extend(jobs)

        # make a dict of job postings from the listing briefs
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('h2', attrs={
                    'class': 'title'}).text.strip()
                job['company'] = s.find(
                    'div', attrs={'class': 'company'}).text.strip()
                job['location'] = s.find('div', attrs={
                    'class': 'location'}).text.strip()
            except AttributeError:
                continue

            # no blurb is available in monster job soups
            job['blurb'] = ''

            try:
                job['date'] = s.find('time').text.strip()
            except AttributeError:
                job['date'] = ''
            # Captures uuid or int id's, by extracting from URL instead.
            try:
                job['link'] = str(
                    s.find('a', attrs={'data-bypass': 'true'}).get(
                        'href'))
                job['id'] = id_regex.findall(job['link'])[0]
            except AttributeError:
                job['id'] = ''
                job['link'] = ''

            job['provider'] = self.provider

            # key by id
            self.scrape_data[str(job['id'])] = job

        # Apply job pre-filter before scraping blurbs
        super().pre_filter(self.scrape_data, self.provider)

        # search the job link to extract the blurb
        scrape_list = [i for i in self.scrape_data.values()]

        post_date_from_relative_post_age(scrape_list)

        if self.delay_config is not None:
            threads = ThreadPoolExecutor(max_workers=8)
            super().delay_threader(scrape_list, self.get_blurb_ms_w_dly,
                                   self.parse_blurb_ms, threads)
        else:
            with ThreadPoolExecutor(max_workers=8) as threads:
                threads.map(self.search_monster_joblink_for_blurb, scrape_list)
