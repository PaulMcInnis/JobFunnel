## scrapes data off indeed.ca and pickles it

import logging
import requests
import bs4
import re
from threading import Thread
from math import ceil

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
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def search_indeed_page_for_job_soups(self, search, page,
                                         list_of_job_soups):
        """function that scrapes the indeed page for a list of job soups"""
        page_url = '{0}&start={1}'.format(
            search, int(page * self.max_results_per_page))
        logging.info('getting indeed page {} : {}'.format(page, page_url))
        jobs = bs4.BeautifulSoup(
            requests.get(page_url, headers=self.headers).text,
            self.bs4_parser).find_all(
            'div', attrs={'data-tn-component': 'organicJob'})
        list_of_job_soups.extend(jobs)

    def scrape(self):
        """function that scrapes job posting from indeed and pickles it"""
        ## scrape a page of indeed results to a pickle
        logging.info('jobfunnel indeed to pickle running @ ' + self.date_string)

        # form the query string
        for i, s in enumerate(self.search_terms['keywords']):
            if i == 0:
                query = s
            else:
                query += '+' + s

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
        request_HTML = requests.get(search, headers=self.headers)
        soup_base = bs4.BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find(id='searchCount').contents[0].strip()
        num_results = re.sub('.*of ', '', num_results)
        num_results = re.sub(',', '', num_results)
        num_results = re.sub('jobs.*', '', num_results)
        num_results = int(num_results)
        logging.info(
            'Found {0} indeed results for query={1}'.format(num_results, query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / self.max_results_per_page))

        # search the pages to extract the list of job soups
        threads = []
        for page in range(0, pages):
            process = Thread(target=self.search_indeed_page_for_job_soups,
                             args=[search, page, list_of_job_soups])
            process.start()
            threads.append(process)

        for process in threads:
            process.join()

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

            try:
                job['blurb'] = s.find(
                    'div', attrs={'class': 'summary'}).text.strip()
            except AttributeError:
                job['blurb'] = ''

            try:
                job['date'] = s.find(
                    'span', attrs={'class': 'date'}).text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                job['id'] = re.findall(r'id=\"sj_[a-zA-Z0-9]*\"', str(
                    s.find('a',
                        attrs={'class': 'sl resultLink save-job-link'})))[0]
                job['id'] = re.sub('id=\"sj_', '', job['id'])
                job['id'] = re.sub('\"', '', job['id'])
                job['link'] = 'http://www.indeed.{0}/viewjob?jk={1}'.format(
                    self.search_terms['region']['domain'], job['id'])
            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            job['provider'] = self.provider

            filter_non_printables(job)
            post_date_from_relative_post_age(job)

            # key by id
            self.scrape_data[str(job['id'])] = job
