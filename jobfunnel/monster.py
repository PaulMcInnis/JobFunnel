## scrapes data off monster.ca and pickles it

import logging
import requests
import bs4
import re
from threading import Thread
from math import ceil

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age
from .tools.filters import id_filter

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
        logging.info(
            'getting monster search: {}'.format(search))
        request_HTML = requests.get(search, headers=self.headers)
        job_link_soup = bs4.BeautifulSoup(
            request_HTML.text, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescription').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    def scrape(self):
        """function that scrapes job posting from monster and pickles it"""
        ## scrape a page of monster results to a pickle
        logging.info(
            'jobfunnel monster to pickle running @ : ' + self.date_string)
        # ID regex quantifiers
        id_regex = \
            re.compile(
                r'/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})|\d+)')
        # initialize and store date quantifiers as regex objects in list.
        date_regex = [re.compile(r'(\d+)(?:[ +]{1,3})?(?:hour|hr)'),
                      re.compile(r'(\d+)(?:[ +]{1,3})?(?:day|d)'),
                      re.compile(r'(\d+)(?:[ +]{1,3})?month'),
                      re.compile(r'(\d+)(?:[ +]{1,3})?year'),
                      re.compile(r'[tT]oday|[jJ]ust [pP]osted'),
                      re.compile(r'[yY]esterday')]

        # form the query string
        query = '-'.join(self.search_terms['keywords'])

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
        request_HTML = requests.get(search, headers=self.headers)
        soup_base = bs4.BeautifulSoup(request_HTML.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find('h2', 'figure').text.strip()
        num_results = int(re.findall(r'(\d+)', num_results)[0])
        logging.info(
            'Found {} monster results for query={}'.format(num_results, query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / self.max_results_per_page))
        page_url = '{0}&start={1}'.format(search, pages)
        logging.info(
            'getting monster pages 1 to {0} : {1}'.format(pages, page_url))
        jobs = bs4.BeautifulSoup(
            requests.get(page_url, headers=self.headers).text,
            self.bs4_parser).find_all(
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

            post_date_from_relative_post_age(job, date_regex)

            # key by id
            self.scrape_data[str(job['id'])] = job

        # Pop duplicate job ids already in master list
        id_filter(self.scrape_data, super().read_csv(self.master_list_path),
                  self.provider)

        # search the job link to extract the blurb
        scrape_data_list = [i for i in self.scrape_data.values()]
        threads = []
        for job in scrape_data_list:
            if job['provider'] == self.provider:
                process = Thread(target=self.search_monster_joblink_for_blurb,
                                 args=[job])
                process.start()
                threads.append(process)

        for process in threads:
            process.join()
