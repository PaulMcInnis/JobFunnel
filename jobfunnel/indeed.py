import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
from logging import info as log_info
from math import ceil
from requests import get
from time import sleep

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age


class Indeed(JobFunnel):

    def __init__(self, args):
        super().__init__(args)
        self.provider = 'indeed'
        self.max_results_per_page = 50
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.indeed.{0}/'.format(
                self.search_terms['region']['domain']),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def search_indeed_page_for_job_soups(self, search, page,
                                         list_of_job_soups):
        """function that scrapes the indeed page for a list of job soups"""
        page_url = f'{search}&start={int(page * self.max_results_per_page)}'
        log_info(f'getting indeed page {page} : {page_url}')
        jobs = BeautifulSoup(get(page_url, headers=self.headers).text,
                             self.bs4_parser).find_all(
            'div', attrs={'data-tn-component': 'organicJob'})

        list_of_job_soups.extend(jobs)

    def search_indeed_joblink_for_blurb(self, job):
        """function that scrapes the indeed job link for the blurb"""
        search = job['link']
        log_info(f'getting indeed page: {search}')
        job_link_soup = BeautifulSoup(
            get(search, headers=self.headers).text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='jobDescriptionText').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def get_blurb_in_w_dly(self, job, delay):
        """
        function that gets blurb from indeed and uses request delaying
        """
        sleep(delay)
        search = job['link']
        log_info(f'getting indeed search: {search}')
        res = get(search, headers=self.headers).text
        return job, res

    def parse_blurb_in(self, job, html):
        """
        stores parsed job description into job dict
        """
        job_link_soup = BeautifulSoup(
            html, self.bs4_parser)
        try:
            job['blurb'] = job_link_soup.find(
                id='jobDescriptionText').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)


    def scrape(self):
        """function that scrapes job posting from indeed and pickles it"""
        log_info('jobfunnel indeed to pickle running @ ' + self.date_string)

        # ID regex quantifier
        id_regex = re.compile(r'id=\"sj_([a-zA-Z0-9]*)\"')

        # form the query string
        query = '+'.join(self.search_terms['keywords'])

        # build the job search URL
        search = 'http://www.indeed.{0}/jobs?q={1}&l={2}%2C+{3}&radius={4}' \
                 '&limit={5}&filter={6}'.format(
            self.search_terms['region']['domain'],
            query,
            self.search_terms['region']['city'],
            self.search_terms['region']['province'],
            self.search_terms['region']['radius'],
            self.max_results_per_page,
            int(self.similar_results))

        # get the HTML data, initialize bs4 with lxml
        request_HTML = get(search, headers=self.headers)
        soup_base = BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        # Now with less regex!
        num_results = soup_base.find(id='searchCountPages').contents[0].strip()
        num_results = int(re.findall(r'f (\d+) ',
                                     num_results.replace(',', ''))[0])

        log_info(f'Found {num_results} indeed results for query={query}')

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / self.max_results_per_page))

        threads = ThreadPoolExecutor(max_workers=8)
        wait([threads.submit(self.search_indeed_page_for_job_soups, search,
                             page, list_of_job_soups)
              for page in range(0, pages)])

        # make a dict of job postings from the listing briefs
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('a', attrs={
                    'data-tn-element': 'jobTitle'}).text.strip()
                job['company'] = s.find(
                    'span', attrs={'class': 'company'}).text.strip()
                job['location'] = s.find('span', attrs={
                    'class': 'location'}).text.strip()
            except AttributeError:
                continue

            job['blurb'] = ''

            try:
                job['date'] = s.find(
                    'span', attrs={'class': 'date'}).text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                # Added capture group so to only capture id once matched.
                job['id'] = id_regex.findall(str(
                    s.find('a',
                           attrs={'class': 'sl resultLink save-job-link'})))[0]

                job['link'] = 'http://www.indeed.{0}/viewjob?jk={1}'.format(
                    self.search_terms['region']['domain'], job['id'])

            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            filter_non_printables(job)

            # key by id
            self.scrape_data[str(job['id'])] = job

            job['provider'] = self.provider

        scrape_list = [i for i in self.scrape_data.values()]

        post_date_from_relative_post_age(scrape_list)

        # Apply job pre-filter before scraping blurbs
        super().pre_filter(self.scrape_data, self.provider)

        # Checks if delay is set or not, then proceed to scrape blurbs
        if self.delay_config is not None:
            # Calls super class to run delay specific threading logic
            super().delay_threader(scrape_list, self.get_blurb_in_w_dly,
                                   self.parse_blurb_in, threads)
        else:
            # Maps jobs to threads which shutdown when finished
            threads.map(self.search_indeed_joblink_for_blurb, scrape_list)
            threads.shutdown()
