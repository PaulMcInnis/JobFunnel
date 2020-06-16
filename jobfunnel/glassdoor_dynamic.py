import re

from bs4 import BeautifulSoup
from selenium import webdriver
from concurrent.futures import ThreadPoolExecutor, wait
from logging import info as log_info
from math import ceil
from requests import post
from time import sleep, time


from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age, get_webdriver
from .glassdoor_base import GlassDoorBase


class GlassDoorDynamic(GlassDoorBase):
    """The Dynamic Version of the GlassDoor scraper, that uses selenium to scrape job postings."""

    def __init__(self, args):
        super().__init__(args)
        self.provider = 'glassdoordynamic'

        # initialize the webdriver
        self.driver = get_webdriver()

    def get_search_url(self, method='get'):
        """gets the glassdoor search url"""
        # form the location lookup request data
        data = {'term': self.search_terms['region']
                ['city'], 'maxLocationsToReturn': 10}

        # form the location lookup url
        location_url = 'https://www.glassdoor.co.in/findPopularLocationAjax.htm?'

        # get the location id for search location
        location_response = self.s.post(
            location_url, headers=self.location_headers, data=data
        ).json()

        if method == 'get':
            # form job search url
            search = (
                'https://www.glassdoor.{0}/Job/jobs.htm?'
                'clickSource=searchBtn&sc.keyword={1}&locT=C&locId={2}&jobType=&radius={3}'.format(
                    self.search_terms['region']['domain'],
                    self.query,
                    location_response[0]['locationId'],
                    self.convert_radius(self.search_terms['region']['radius']),
                )
            )

            return search
        elif method == 'post':
            # form the job search url
            search = (
                f'https://www.glassdoor.'
                f"{self.search_terms['region']['domain']}/Job/jobs.htm"
            )

            # form the job search data
            data = {
                'clickSource': 'searchBtn',
                'sc.keyword': self.query,
                'locT': 'C',
                'locId': location_response[0]['locationId'],
                'jobType': '',
                'radius': self.convert_radius(self.search_terms['region']['radius']),
            }

            return search, data
        else:
            raise ValueError(f'No html method {method} exists')

    def search_page_for_job_soups(self, page, url, job_soup_list):
        """function that scrapes the glassdoor page for a list of job soups"""
        log_info(f'getting glassdoor page {page} : {url}')

        self.driver.get(url)
        job = BeautifulSoup(self.driver.page_source, self.bs4_parser).find_all(
            'li', attrs={'class', 'jl'}
        )
        job_soup_list.extend(job)

    def search_joblink_for_blurb(self, job):
        """function that scrapes the glassdoor job link for the blurb"""
        search = job['link']
        log_info(f'getting glassdoor search: {search}')

        self.driver.get(search)
        job_link_soup = BeautifulSoup(self.driver.page_source, self.bs4_parser)

        try:
            job['blurb'] = job_link_soup.find(
                id='JobDescriptionContainer').text.strip()
        except AttributeError:
            job['blurb'] = ''

        filter_non_printables(job)

    # split apart above function into two so gotten blurbs can be parsed
    # while others blurbs are being obtained
    def get_blurb_with_delay(self, job, delay):
        """gets blurb from glassdoor job link and sets delays for requests"""
        sleep(delay)

        search = job['link']
        log_info(f'delay of {delay:.2f}s, getting glassdoor search: {search}')

        self.driver.get(search)
        res = self.driver.page_source
        return job, res

    def scrape(self):
        """function that scrapes job posting from glassdoor and pickles it"""
        log_info(f'jobfunnel glassdoor to pickle running @ {self.date_string}')

        # get the se arch url
        search = self.get_search_url()

        # get the html data, initialize bs4 with lxml
        self.driver.get(search)

        # create the soup base
        soup_base = BeautifulSoup(self.driver.page_source, self.bs4_parser)
        num_res = soup_base.find('p', attrs={
            'class', 'jobsCount'})
        while(num_res is None):
            print("It looks like that Glassdoor might require you to fill out a CAPTCHA form. Follow these steps if it does ask you to complete a CAPTCHA:"
                  "\n 1.Refresh the glassdoor site in the new browser window that just popped up.\n" " 2.Then complete the CAPTCHA in the browser.\n 3.Press Enter to continue")
        # wait for user to complete CAPTCHA
            input()
            soup_base = BeautifulSoup(self.driver.page_source, self.bs4_parser)
            num_res = soup_base.find('p', attrs={'class', 'jobsCount'})
        # scrape total number of results, and calculate the # pages needed

        num_res = num_res.text.strip()
        num_res = int(re.findall(r'(\d+)', num_res.replace(',', ''))[0])
        log_info(
            f'Found {num_res} glassdoor results for query=' f'{self.query}')

        pages = int(ceil(num_res / self.max_results_per_page))

        # init list of job soups
        job_soup_list = []
        # init threads
        threads = ThreadPoolExecutor(max_workers=1)
        # init futures list
        fts = []

        # search the pages to extract the list of job soups
        for page in range(1, pages + 1):
            if page == 1:
                fts.append(  # append thread job future to futures list
                    threads.submit(
                        self.search_page_for_job_soups,
                        page,
                        self.driver.current_url,
                        job_soup_list,
                    )
                )
            else:
                # gets partial url for next page
                part_url = (
                    soup_base.find('li', attrs={'class', 'next'}).find(
                        'a').get('href')
                )
                # uses partial url to construct next page url
                page_url = re.sub(
                    r'.htm',
                    'IP' + str(page) + '.htm',
                    f'https://www.glassdoor.'
                    f"{self.search_terms['region']['domain']}"
                    f'{part_url}',
                )

                fts.append(  # append thread job future to futures list
                    threads.submit(
                        self.search_page_for_job_soups, page, page_url, job_soup_list
                    )
                )
        wait(fts)  # wait for all scrape jobs to finish
        # close and shutdown the web driver
        self.driver.close()
        # make a dict of job postings from the listing briefs
        for s in job_soup_list:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find_all('a', attrs={'class', 'jobTitle'})[
                    1
                ].text.strip()
                job['company'] = s.find(
                    'div', attrs={'class', 'jobEmpolyerName'}
                ).text.strip()
                job['location'] = s.find(
                    'span', attrs={'class', 'loc'}).text.strip()
            except AttributeError:
                continue

            # set blurb to none for now
            job['blurb'] = ''

            try:
                labels = s.find_all('div', attrs={'class', 'jobLabel'})
                job['tags'] = '\n'.join(
                    [l.text.strip() for l in labels if l.text.strip() != 'New']
                )
            except AttributeError:
                job['tags'] = ''

            try:
                # dynamic way of fetching date
                job['date'] = s.find('div', attrs={
                                     'class', 'd-flex align-items-end pl-std minor css-65p68w'}).text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                job['id'] = s.get('data-id')
                job['link'] = (
                    s.find('div', attrs={'class', 'logoWrap'}).find(
                        'a').get('href')
                )

            except (AttributeError, IndexError):
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

        # checks if delay is set or not, then extracts blurbs from job links
        if self.delay_config is not None:
            # calls super class to run delay specific threading logic
            super().delay_threader(
                scrape_list, self.get_blurb_with_delay, self.parse_blurb, threads
            )

        else:  # maps jobs to threads and cleans them up when done
            # start time recording
            start = time()

            # maps jobs to threads and cleans them up when done
            threads.map(self.search_joblink_for_blurb, scrape_list)
            threads.shutdown()

            # end and print recorded time
            end = time()
            print(f'{self.provider} scrape job took {(end - start):.3f}s')
