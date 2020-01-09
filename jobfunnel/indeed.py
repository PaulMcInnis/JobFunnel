import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
from logging import info as log_info
from math import ceil
from requests import get
from time import sleep, time

from jobfunnel import JobFunnel, MASTERLIST_HEADER
from tools.tools import filter_non_printables
from tools.tools import post_date_from_relative_post_age


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

    def convert_indeed_radius(self, radius):
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

    def search_indeed_page_for_job_soups(self, search, page, job_soup_list):
        """function that scrapes the indeed page for a list of job soups"""
        url = f'{search}&start={int(page * self.max_results_per_page)}'
        log_info(f'getting indeed page {page} : {url}')

        jobs = BeautifulSoup(
            get(url, headers=self.headers).text, self.bs4_parser).\
            find_all('div', attrs={'data-tn-component': 'organicJob'})

        job_soup_list.extend(jobs)

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
        """gets blurb from indeed job link and sets delays for requests"""
        sleep(delay)
        search = job['link']

        log_info(f'delay of {delay}\'s, getting indeed search: {search}')
        # log_info(f'getting indeed search: {search}')

        res = get(search, headers=self.headers).text
        return job, res

    def parse_blurb_in(self, job, html):
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

        # ID regex quantifier
        id_regex = re.compile(r'id=\"sj_([a-zA-Z0-9]*)\"')

        # form the query string
        query = '+'.join(self.search_terms['keywords'])
        # write region dict to vars, to reduce lookup load in loops
        domain = self.search_terms['region']['domain']
        city = self.search_terms['region']['city']
        province = self.search_terms['region']['province']
        radius = self.convert_indeed_radius(
            self.search_terms['region']['radius'])

        # form job search url
        search = (f'http://www.indeed.{domain}'
                  f'/jobs?q={query}&l={city}%2C+{province}'
                  f"&radius={radius}"
                  f"&limit={self.max_results_per_page}"
                  f"&filter={int(self.similar_results)}")

        # get the HTML data, initialize bs4 with lxml
        request_HTML = get(search, headers=self.headers)
        soup_base = BeautifulSoup(request_HTML.text, self.bs4_parser)

        # Parse total results, and calculate the # of pages needed
        # Now with less regex!
        num_res = soup_base.find(id='searchCountPages').contents[0].strip()
        num_res = int(re.findall(r'f (\d+) ', num_res.replace(',', ''))[0])
        log_info(f'Found {num_res} indeed results for query={query}')

        pages = int(ceil(num_res / self.max_results_per_page))

        # Init list of job soups
        job_soup_list = []
        # Init threads
        threads = ThreadPoolExecutor(max_workers=8)
        # Init futures list
        fts = []

        # Replaces plus signs with dashes for storing query in master_list
        query = query.replace('+', '-')

        # scrape soups for all the pages containing jobs it found
        for page in range(0, pages):
            fts.append(  # Append thread job future to futures list
                threads.submit(self.search_indeed_page_for_job_soups,
                               search, page, job_soup_list))
        wait(fts)  # Wait for all scrape jobs to finish

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
                    'table', attrs={'class': 'jobCardShelfContainer'}).\
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
                # Added capture group so to only capture id once matched.
                job['id'] = id_regex.findall(str(s.find('a', attrs={
                    'class': 'sl resultLink save-job-link'})))[0]
                job['link'] = (f"http://www.indeed.{domain}"
                               f"/viewjob?jk={job['id']}")

            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            job['query'] = query
            job['provider'] = self.provider

            # key by id
            self.scrape_data[str(job['id'])] = job

        # Stores references to jobs in list to be used in blurb retrieval
        scrape_list = [i for i in self.scrape_data.values()]

        # Converts job date formats into a standard date format
        post_date_from_relative_post_age(scrape_list)

        # Apply job pre-filter before scraping blurbs
        super().pre_filter(self.scrape_data, self.provider)

        # Checks if delay is set or not, then extracts blurbs from job links
        if self.delay_config is not None:
            # Calls super class to run delay specific threading logic
            super().delay_threader(scrape_list, self.get_blurb_in_w_dly,
                                   self.parse_blurb_in, threads)

        else:
            # Start time recording
            start = time()
            # maps jobs to threads and cleans them up when done
            threads.map(self.search_indeed_joblink_for_blurb, scrape_list)
            threads.shutdown()
            # End and print recorded time
            end = time()
            print(f'{self.provider} scrape job took {(end - start):.3f}s')
