import re


from collections import defaultdict as dd
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
from logging import info as log_info
from math import ceil
from requests import get
from time import sleep, time

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age
from  jobfunnel.database import country_indeed


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
            'referer': '{0}/'.format(
                country_indeed[self.search_terms['region']['country']]),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        self.query = '+'.join(self.search_terms['keywords'])

    def convert_radius(self, radius):
        """function that quantizes the user input radius to a valid radius
           value: 5, 10, 15, 25, 50, 100, and 200 kilometers or miles"""
        if radius < 5:
            radius = 0
        elif 5 <= radius < 10:
            radius = 5
        elif 10 <= radius < 15:
            radius = 10
        elif 15 <= radius < 25:
            radius = 15
        elif 25 <= radius < 50:
            radius = 25
        elif 50 <= radius < 100:
            radius = 50
        elif 100 <= radius:
            radius = 100
        return radius

    def get_search_url(self, method='get'):
        """gets the indeed search url"""
        if method == 'get':
            # form job search url
            search = ('{0}/jobs?'
                      'q={1}&l={2}&radius={3}&limit={4}&filter={5}'.format(
                    country_indeed[self.search_terms['region']['country']],
                self.query,
                self.search_terms['region']['city'],
                self.convert_radius(self.search_terms['region']['radius']),
                self.max_results_per_page,
                int(self.similar_results)))
                #print(search)
            #print(country_indeed)

            return search
        elif method == 'post':
            # @TODO implement post style for indeed
            raise NotImplementedError()
        else:
            raise ValueError(f'No html method {method} exists')

    def search_page_for_job_soups(self, search, page, job_soup_list):
        """function that scrapes the indeed page for a list of job soups"""
        url = f'{search}&start={int(page * self.max_results_per_page)}'
        log_info(f'getting indeed page {page} : {url}')

        jobs = BeautifulSoup(
            self.s.get(url, headers=self.headers).text, self.bs4_parser). \
            find_all('div', attrs={'data-tn-component': 'organicJob'})

        job_soup_list.extend(jobs)

    def search_joblink_for_blurb(self, job):
        """function that scrapes the indeed job link for the blurb"""
        search = job['link']
        log_info(f'getting indeed page: {search}')

        job_link_soup = BeautifulSoup(
            self.s.get(search, headers=self.headers).text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='jobDescriptionText').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def get_blurb_with_delay(self, job, delay):
        """gets blurb from indeed job link and sets delays for requests"""
        sleep(delay)

        search = job['link']
        log_info(f'delay of {delay:.2f}s, getting indeed search: {search}')

        res = self.s.get(search, headers=self.headers).text
        return job, res

    def parse_blurb(self, job, html):
        """parses and stores job description into dict entry"""
        job_link_soup = BeautifulSoup(html, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='jobDescriptionText').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def scrape(self):
        """function that scrapes job posting from indeed and pickles it"""
        log_info(f'jobfunnel indeed to pickle running @ {self.date_string}')

        # get the search url
        search = self.get_search_url()
        print('search',search)

        # get the html data, initialize bs4 with lxml
        request_html = self.s.get(search, headers=self.headers)

        # create the soup base
        soup_base = BeautifulSoup(request_html.text, self.bs4_parser)

        # parse total results, and calculate the # of pages needed
        
        num_res = soup_base.find(id='searchCountPages').contents[0].strip()
        num_res = int(re.findall(r'f (\d+) ', num_res.replace(',', ''))[0])
        log_info(f'Found {num_res} indeed results for query='
                 f'{self.query}')

        pages = int(ceil(num_res / self.max_results_per_page))

        # init list of job soups
        job_soup_list = []
        # init threads
        threads = ThreadPoolExecutor(max_workers=8)
        # init futures list
        fts = []

        # scrape soups for all the pages containing jobs it found
        for page in range(0, pages):
            fts.append(  # append thread job future to futures list
                threads.submit(self.search_page_for_job_soups,
                               search, page, job_soup_list))
        wait(fts)  # wait for all scrape jobs to finish

        # id regex quantifiers
        id_regex = re.compile(r'id=\"sj_([a-zA-Z0-9]*)\"')

        # make a dict of job postings from the listing briefs
        for s in job_soup_list:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('a', attrs={
                    'data-tn-element': 'jobTitle'}).text.strip()
                job['company'] = s.find('span', attrs={
                    'class': 'company'}).text.strip()
                job['location'] = s.find('span', attrs={
                    'class': 'location'}).text.strip()
            except AttributeError:
                continue

            job['blurb'] = ''

            try:
                table = s.find(
                    'table', attrs={'class': 'jobCardShelfContainer'}). \
                    find_all('td', attrs={'class': 'jobCardShelfItem'})
                job['tags'] = "\n".join([td.text.strip() for td in table])
            except AttributeError:
                job['tags'] = ''

            try:
                job['date'] = s.find('span', attrs={
                    'class': 'date'}).text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                job['id'] = id_regex.findall(str(s.find('a', attrs={
                    'class': 'sl resultLink save-job-link'})))[0]
                temp = country_indeed[self.search_terms['region']['country']]
                job['link'] = (f"{temp}"
                               f"/viewjob?jk={job['id']}")

            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            job['query'] = self.query
            job['provider'] = self.provider

            # key by id
            self.scrape_data[str(job['id'])] = job

        # stores references to jobs in list to be used in blurb retrieval
        scrape_list = [i for i in self.scrape_data.values()]

        # converts job date formats into a standard date format
        post_date_from_relative_post_age(scrape_list)

        # apply job pre-filter before scraping blurbs
        super().pre_filter(self.scrape_data, self.provider)

        # checks if delay is set or not, then extracts blurbs from job links
        if self.delay_config is not None:
            # calls super class to run delay specific threading logic
            super().delay_threader(scrape_list, self.get_blurb_with_delay,
                                   self.parse_blurb, threads)

        else:
            # start time recording
            start = time()

            # maps jobs to threads and cleans them up when done
            threads.map(self.search_joblink_for_blurb, scrape_list)
            threads.shutdown()

            # end and print recorded time
            end = time()
            print(f'{self.provider} scrape job took {(end - start):.3f}s')
