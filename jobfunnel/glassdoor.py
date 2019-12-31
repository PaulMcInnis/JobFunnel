import os
import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait, as_completed
from logging import info as log_info, error
from math import ceil
from requests import post
from time import sleep

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age
from .tools.delay import random_delay
from .tools.filters import id_filter


class GlassDoor(JobFunnel):

    def __init__(self, args):
        super().__init__(args)
        self.provider = 'glassdoor'
        self.max_results_per_page = 30
        self.delay = 0
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                self.search_terms['region']['domain']),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
        self.location_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,'
                      'image/webp,*/*;q=0.01',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                self.search_terms['region']['domain']),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def convert_glassdoor_radius(self, radius):
        """function that quantizes the user input radius to a valid
           radius value: 10, 20, 30, 50 and 100 kilometers"""

        if radius < 10:
            radius = 0
        elif 10 <= radius < 20:
            radius = 10
        elif 20 <= radius < 30:
            radius = 20
        elif 30 <= radius < 50:
            radius = 30
        elif 50 <= radius < 100:
            radius = 50
        elif radius >= 100:
            radius = 100

        glassdoor_radius = {
            0: 0,
            10: 6,
            20: 12,
            30: 19,
            50: 31,
            100: 62
        }

        return glassdoor_radius[radius]

    def search_glassdoor_page_for_job_soups(self, data, page, page_url,
                                            list_of_job_soups):
        """function that scrapes the glassdoor page for a list of job soups"""
        log_info(
            'getting glassdoor page {0} : {1}'.format(page, page_url))
        job = BeautifulSoup(
            post(page_url, headers=self.headers, data=data).text,
            self.bs4_parser).find_all('li', attrs={'class', 'jl'})
        list_of_job_soups.extend(job)

    def search_glassdoor_joblink_for_blurb(self, job):
        """function that scrapes the glassdoor job link for the blurb"""
        search = job['link']
        log_info('getting glassdoor search: {}'.format(search))
        job_link_soup = BeautifulSoup(
            post(search, headers=self.location_headers).text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescriptionContainer').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    # Split apart above function into two so gotten blurbs can be parsed while
    # while others blurbs are being obtained.
    def get_blurb_gd_w_dly(self, job, delay):
        """
        function that gets blurb from glassdoor and uses request delaying
        """
        sleep(delay)
        search = job['link']
        log_info('getting glassdoor search: {}'.format(search))
        res = post(search, headers=self.location_headers).text
        return job, res

    def parse_blurb_gd(self, job, html):
        """
        stores parsed job description into job dict
        """
        job_link_soup = BeautifulSoup(html, self.bs4_parser)
        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescriptionContainer').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def scrape(self):
        """function that scrapes job posting from glassdoor and pickles it"""
        log_info(
            'jobfunnel glassdoor to pickle running @' + self.date_string)

        # form the query string
        query = '-'.join(self.search_terms['keywords'])

        data = {'term': self.search_terms['region']['city'],
                'maxLocationsToReturn': 10}

        location_url = \
            'https://www.glassdoor.co.in/findPopularLocationAjax.htm?'

        # get the location id for search location
        location_response = \
            post(location_url, headers=self.location_headers, data=data).json()

        job_listing_url = 'https://www.glassdoor.{0}/Job/jobs.htm'.format(
            self.search_terms['region']['domain'])

        # form data to get job results
        data = {
            'clickSource': 'searchBtn',
            'sc.keyword': query,
            'locT': 'C',
            'locId': location_response[0]['locationId'],
            'jobType': '',
            'radius': self.convert_glassdoor_radius(
                self.search_terms['region']['radius'])
        }

        # get the HTML data, initialize bs4 with lxml
        request_HTML = post(job_listing_url, headers=self.headers, data=data)
        soup_base = BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        # Now with less regex!
        num_res = soup_base.find(
            'p', attrs={'class', 'jobsCount'}).text.strip()
        num_res = int(re.findall(r'(\d+)', num_res.replace(',', ''))[0])
        log_info(
            'Found {} glassdoor results for query={}'.format(num_res, query))
        pages = int(ceil(num_res / self.max_results_per_page))

        list_of_job_soups = []

        # search the pages to extract the list of job soups
        threads = ThreadPoolExecutor(max_workers=8)
        res = [threads.submit(self.search_glassdoor_page_for_job_soups, data,
                              page, request_HTML.url, list_of_job_soups)
               if page == 1 else threads.submit(
            self.search_glassdoor_page_for_job_soups, data, page, re.sub(
                r'_IP\d+\.', "_IP" + str(page) + ".",
                'https://www.glassdoor.{0}{1}'.format(
                    self.search_terms['region']['domain'], soup_base.find(
                        'li', attrs={'class', 'next'}).find('a').get('href'))
            )) for page in range(1, pages + 1)]
        wait(res)

        # make a dict of job postings from the listing briefs
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('div', attrs={'class',
                                                    'jobContainer'}). \
                    find('a', attrs={'class', 'jobLink jobInfoItem jobTitle'},
                         recursive=False).text.strip()
                job['company'] = \
                    s.find('div',
                           attrs={'class',
                                  'jobInfoItem jobEmpolyerName'}).text.strip()
                job['location'] = s.get('data-job-loc')
            except AttributeError:
                continue

            # no blurb is available in glassdoor job soups
            job['blurb'] = None

            try:
                job['date'] = s.find('div', attrs={'class', 'jobLabels'}).find(
                    'span', attrs={'class', 'jobLabel nowrap'}).text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                job['id'] = s.get('data-id')
                job['link'] = 'https://www.glassdoor.{0}{1}'.format(
                    self.search_terms['region']['domain'],
                    s.find('div', attrs={'class', 'logoWrap'}).find('a').get(
                        'href'))
            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            job['provider'] = self.provider

            # key by id
            self.scrape_data[str(job['id'])] = job

        # Pops duplicate job ids already in master list and
        # also in the duplicate list
        if os.path.exists(self.master_list_path):
            id_filter(self.scrape_data, super().read_csv(
                self.master_list_path), self.provider)
            # Checks duplicates file as well if it exists
            if os.path.exists(self.duplicate_list_path):
                id_filter(self.scrape_data, super().read_csv(
                    self.duplicate_list_path), self.provider)

        # search the job link to extract the blurb
        scrape_list = [i for i in self.scrape_data.values()]

        # Takes our scrape data and filters date all out once
        post_date_from_relative_post_age(scrape_list)

        if self.delay_config is not None:
            # Calculates delay and returns list of delays
            delays = random_delay(len(scrape_list), self.delay_config)
            # Zips delays and scrape list as jobs for thread pool
            scrape_jobs = zip(scrape_list, delays)
            # Submits jobs and stores futures in dict
            results = {threads.submit(self.get_blurb_gd_w_dly, job, delays):
                           job['id'] for job, delays in scrape_jobs}
            # Loops through futures and removes each if successfully parsed
            while results:
                # Gets each future as they complete
                for future in as_completed(results):
                    try:
                        job, html = future.result() # Stores results
                        self.parse_blurb_gd(job, html) #
                    except Exception:
                        pass
                    del results[future]
            threads.shutdown()
        else:
            # Maps jobs to threads which shutdown when finished
            threads.map(self.search_glassdoor_joblink_for_blurb, scrape_list)
            threads.shutdown()
