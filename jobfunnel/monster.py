import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from logging import info as log_info
from math import ceil
from requests import get
from time import sleep, time

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age


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

    def convert_monster_radius(self, radius):
        """function that quantizes the user input radius to a valid radius
        in either kilometers or miles"""
        if self.search_terms['region']['domain'] == 'com':
            if radius < 5:
                radius = 0
            elif 5 <= radius < 10:
                radius = 5
            elif 10 <= radius < 20:
                radius = 10
            elif 20 <= radius < 30:
                radius = 20
            elif 30 <= radius < 40:
                radius = 30
            elif 40 <= radius < 50:
                radius = 40
            elif 50 <= radius < 60:
                radius = 50
            elif 60 <= radius < 75:
                radius = 60
            elif 75 <= radius < 100:
                radius = 75
            elif 100 <= radius < 150:
                radius = 100
            elif 150 <= radius < 200:
                radius = 150
            elif 200 <= radius:
                radius = 200
            # Now I know why they call themselves monster
        else:
            if radius < 5:
                radius = 0
            elif 5 <= radius < 10:
                radius = 5
            elif 10 <= radius < 20:
                radius = 10
            elif 20 <= radius < 50:
                radius = 20
            elif 50 <= radius < 100:
                radius = 50
            elif 100 <= radius:
                radius = 100

        return radius

    def search_monster_joblink_for_blurb(self, job):
        """function that scrapes the monster job link for the blurb"""
        search = job['link']
        log_info(f'getting monster search: {search}')

        job_link_soup = BeautifulSoup(
            get(search, headers=self.headers).text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescription').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    # Split apart above function into two so gotten blurbs can be parsed while
    # while others blurbs are being obtained.
    def get_blurb_ms_w_dly(self, job, delay):
        """gets blurb from monster job link and sets delays for requests"""
        sleep(delay)

        search = job['link']
        log_info(f'getting monster search: {search}')

        res = get(search, headers=self.headers).text
        return job, res

    def parse_blurb_ms(self, job, html):
        """parses and stores job description into dict entry"""
        job_link_soup = BeautifulSoup(html, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescription').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def scrape(self):
        """function that scrapes job posting from monster and pickles it"""
        log_info(f'jobfunnel monster to pickle running @ {self.date_string}')

        # ID regex quantifiers
        id_regex = re.compile(r'/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f'
                              r']{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})|\d+)')

        # form the query string
        query = '-'.join(self.search_terms['keywords'])
        # write region dict to vars, to reduce lookup load in loops
        domain = self.search_terms['region']['domain']
        city = self.search_terms['region']['city']
        province = self.search_terms['region']['province']
        radius = self.convert_monster_radius(
            self.search_terms['region']['radius'])

        # build the job search URL
        search = (f'https://www.monster.{domain}'
                  f'/jobs/search/?q={query}'
                  f'&where={city}__2C-{province}'
                  f'&intcid=skr_navigation_nhpso_searchMain'
                  f'&rad={radius}&where={city}__2c-{province}')

        # get the HTML data, initialize bs4 with lxml
        request_HTML = get(search, headers=self.headers)
        soup_base = BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        # Now with less regex!
        num_res = soup_base.find('h2', 'figure').text.strip()
        num_res = int(re.findall(r'(\d+)', num_res)[0])
        log_info(f'Found {num_res} monster results for query={query}')

        pages = int(ceil(num_res / self.max_results_per_page))
        # scrape soups for all the pages containing jobs it found
        page_url = f'{search}&start={pages}'
        log_info(f'getting monster pages 1 to {pages} : {page_url}')

        jobs = BeautifulSoup(
            get(page_url, headers=self.headers).text, self.bs4_parser). \
            find_all('div', attrs={'class': 'flex-row'})

        job_soup_list = []
        job_soup_list.extend(jobs)

        # make a dict of job postings from the listing briefs
        for s in job_soup_list:
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
                job['link'] = str(s.find('a', attrs={
                    'data-bypass': 'true'}).get('href'))
                job['id'] = id_regex.findall(job['link'])[0]
            except AttributeError:
                job['id'] = ''
                job['link'] = ''

            job['query'] = query
            job['provider'] = self.provider

            # key by id
            self.scrape_data[str(job['id'])] = job

        # Apply job pre-filter before scraping blurbs
        super().pre_filter(self.scrape_data, self.provider)

        # Stores references to jobs in list to be used in blurb retrieval
        scrape_list = [i for i in self.scrape_data.values()]

        # Converts job date formats into a standard date format
        post_date_from_relative_post_age(scrape_list)

        threads = ThreadPoolExecutor(max_workers=8)
        # Checks if delay is set or not, then extracts blurbs from job links
        if self.delay_config is not None:
            # Calls super class to run delay specific threading logic
            super().delay_threader(scrape_list, self.get_blurb_ms_w_dly,
                                   self.parse_blurb_ms, threads)
        else:
            # Start time recording
            start = time()
            # maps jobs to threads and cleans them up when done
            threads.map(self.search_monster_joblink_for_blurb, scrape_list)
            threads.shutdown()
            # End and print recorded time
            end = time()
            print(f'{self.provider} scrape job took {(end - start):.3f}s')
