## scrapes data off monster.ca and pickles it

import logging
import requests
import bs4
import re
import os
from math import ceil

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age

class Monster(JobFunnel):

    def __init__(self, args):
        super().__init__(args)
        self.max_results_per_page = 25

    def scrape(self):
        """function that scrapes job posting from monster and pickles it"""
        ## scrape a page of monster results to a pickle
        logging.info(
            'jobfunnel monster to pickle running @ : ' + self.date_string)

        # form the query string
        for i, s in enumerate(self.search_terms['keywords']):
            if i == 0:
                query = s
            else:
                query += '-' + s

        # build the job search URL
        search = 'https://www.monster.{0}/jobs/search/?q={1}&where={2}__2C-{3}'\
                 '&intcid=skr_navigation_nhpso_searchMain&rad={4}&where={2}__'\
                 '2c-{3}'.format(
            self.search_terms['region']['domain'],
            query,
            self.search_terms['region']['city'],
            self.search_terms['region']['province'],
            self.search_terms['region']['radius'])

        # get the HTML data, initialize bs4 with lxml
        request_HTML = requests.get(search)
        soup_base = bs4.BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find('h2', 'figure').text.strip()
        num_results = re.sub('\(', '', num_results)
        num_results = re.sub('[a-zA-Z ]*\)', '', num_results)
        num_results = int(num_results)
        logging.info(
            'Found {} monster results for query={}'.format(num_results, query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / self.max_results_per_page))
        page_url = '{0}&start={1}'.format(search, pages)
        logging.info(
            'getting monster pages 1 to {0} : {1}'.format(pages, page_url))
        jobs = bs4.BeautifulSoup(
            requests.get(page_url).text, self.bs4_parser).find_all(
                'div', attrs={'class': 'flex-row'})
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

            try:
                job['id'] = str(
                    s.find('a', attrs={'data-bypass': 'true'}).get(
                        'data-m_impr_j_jobid'))
                job['link'] = str(
                    s.find('a', attrs={'data-bypass': 'true'}).get(
                        'href'))
            except (AttributeError):
                job['id'] = ''
                job['link'] = ''

            # traverse the job link to extract the blurb
            search = job['link']
            logging.info(
                'getting monster search: {}'.format(search))
            request_HTML = requests.get(search)
            job_link_soup = bs4.BeautifulSoup(
                request_HTML.text, self.bs4_parser)

            try:
                job['blurb'] = job_link_soup.find(
                    id='JobDescription').text.strip()
            except AttributeError:
                job['blurb'] = ''

            filter_non_printables(job)
            post_date_from_relative_post_age(job)

            # key by id
            self.scrape_data[str(job['id'])] = job
