import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from logging import info as log_info
from math import ceil
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
        # Sets headers as default on Session object
        self.s.headers.update(self.headers)
        # Concatenates keywords with '-' and encodes spaces as '-'
        self.query = '-'.join(self.search_terms['keywords']).replace(' ', '-')

    def convert_radius(self, radius):
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
            elif radius >= 200:
                radius = 200
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
            elif radius >= 100:
                radius = 100

        return radius

    def get_search_url(self, method='get'):
        """gets the monster request html"""
        # form job search url
        if method == 'get':
            search = ('https://www.monster.{0}/jobs/search/?'
                      'q={1}&where={2}__2C-{3}&intcid={4}&rad={5}&where={2}__2c-{3}'.format(
                self.search_terms['region']['domain'],
                self.query,
                self.search_terms['region']['city'].replace(' ', "-"),
                self.search_terms['region']['province'],
                'skr_navigation_nhpso_searchMain',
                self.convert_radius(self.search_terms['region']['radius'])))

            return search
        elif method == 'post':
            # @TODO implement post style for monster
            raise NotImplementedError()
        else:
            raise ValueError(f'No html method {method} exists')

    def search_joblink_for_blurb(self, job):
        """function that scrapes the monster job link for the blurb"""
        search = job['link']
        log_info(f'getting monster search: {search}')

        job_link_soup = BeautifulSoup(
            self.s.get(search).text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescription').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    # split apart above function into two so gotten blurbs can be parsed
    # while others blurbs are being obtained
    def get_blurb_with_delay(self, job, delay):
        """gets blurb from monster job link and sets delays for requests"""
        sleep(delay)

        search = job['link']
        log_info(f'delay of {delay:.2f}s, getting monster search: {search}')

        res = self.s.get(search).text
        return job, res

    def parse_blurb(self, job, html):
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

        # get the search url
        search = self.get_search_url()

        # get the html data, initialize bs4 with lxml
        request_html = self.s.get(search)

        # create the soup base
        soup_base = BeautifulSoup(request_html.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_res = soup_base.find('h2', 'figure').text.strip()
        num_res = int(re.findall(r'(\d+)', num_res)[0])
        log_info(f'Found {num_res} monster results for query='
                 f'{self.query}')

        pages = int(ceil(num_res / self.max_results_per_page))
        # scrape soups for all the pages containing jobs it found
        page_url = f'{search}&start={pages}'
        log_info(f'getting monster pages 1 to {pages} : {page_url}')

        jobs = BeautifulSoup(
            self.s.get(page_url).text, self.bs4_parser). \
            find_all('div', attrs={'class': 'flex-row'})

        job_soup_list = []
        job_soup_list.extend(jobs)

        # id regex quantifiers
        id_regex = re.compile(r'/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f'
                              r']{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})|\d+)')

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
            # tags are not supported in monster
            job['tags'] = ''
            try:
                job['date'] = s.find('time').text.strip()
            except AttributeError:
                job['date'] = ''
            # captures uuid or int ids, by extracting from url instead
            try:
                job['link'] = str(s.find('a', attrs={
                    'data-bypass': 'true'}).get('href'))
                job['id'] = id_regex.findall(job['link'])[0]
            except AttributeError:
                job['id'] = ''
                job['link'] = ''

            job['query'] = self.query
            job['provider'] = self.provider

            # key by id
            self.scrape_data[str(job['id'])] = job

         # Do not change the order of the next three statements if you want date_filter to work
         
        # stores references to jobs in list to be used in blurb retrieval
        scrape_list = [i for i in self.scrape_data.values()]
        # converts job date formats into a standard date format
        post_date_from_relative_post_age(scrape_list)
        # apply job pre-filter before scraping blurbs
        super().pre_filter(self.scrape_data, self.provider)

        threads = ThreadPoolExecutor(max_workers=8)
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
