import re

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
from logging import info as log_info
from math import ceil
from requests import post
from time import sleep, time

from .jobfunnel import JobFunnel, MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age
from .glassdoor_base import GlassDoorBase


class GlassDoorStatic(GlassDoorBase):
    def __init__(self, args):
        super().__init__(args)
        self.provider = 'glassdoorstatic'
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                self.search_terms['region']['domain']
            ),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }

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
            # @TODO implement get style for glassdoor
            raise NotImplementedError()
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

    def search_page_for_job_soups(self, data, page, url, job_soup_list):
        """function that scrapes the glassdoor page for a list of job soups"""
        log_info(f'getting glassdoor page {page} : {url}')

        job = BeautifulSoup(
            self.s.post(url, headers=self.headers,
                        data=data).text, self.bs4_parser
        ).find_all('li', attrs={'class', 'jl'})
        job_soup_list.extend(job)

    def search_joblink_for_blurb(self, job):
        """function that scrapes the glassdoor job link for the blurb"""
        search = job['link']
        log_info(f'getting glassdoor search: {search}')
        job_link_soup = BeautifulSoup(
            self.s.post(
                search, headers=self.location_headers).text, self.bs4_parser
        )

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

        res = self.s.post(search, headers=self.location_headers).text
        return job, res

    def scrape(self):
        """function that scrapes job posting from glassdoor and pickles it"""
        log_info(f'jobfunnel glassdoor to pickle running @ {self.date_string}')

        # get the search url and data
        search, data = self.get_search_url(method='post')

        # get the html data, initialize bs4 with lxml
        request_html = self.s.post(search, headers=self.headers, data=data)

        # create the soup base
        soup_base = BeautifulSoup(request_html.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_res = soup_base.find(
            'p', attrs={'class', 'jobsCount'}).text.strip()
        num_res = int(re.findall(r'(\d+)', num_res.replace(',', ''))[0])
        log_info(
            f'Found {num_res} glassdoor results for query=' f'{self.query}')

        pages = int(ceil(num_res / self.max_results_per_page))

        # init list of job soups
        job_soup_list = []
        # init threads
        threads = ThreadPoolExecutor(max_workers=8)
        # init futures list
        fts = []

        # search the pages to extract the list of job soups
        for page in range(1, pages + 1):
            if page == 1:
                fts.append(  # append thread job future to futures list
                    threads.submit(
                        self.search_page_for_job_soups,
                        data,
                        page,
                        request_html.url,
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
                    r'_IP\d+\.',
                    '_IP' + str(page) + '.',
                    f'https://www.glassdoor.'
                    f"{self.search_terms['region']['domain']}"
                    f'{part_url}',
                )

                fts.append(  # append thread job future to futures list
                    threads.submit(
                        self.search_page_for_job_soups,
                        data,
                        page,
                        page_url,
                        job_soup_list,
                    )
                )
        wait(fts)  # wait for all scrape jobs to finish

        # make a dict of job postings from the listing briefs
        for s in job_soup_list:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = (
                    s.find('div', attrs={'class', 'jobContainer'})
                    .find(
                        'a',
                        attrs={'class', 'jobLink jobInfoItem jobTitle'},
                        recursive=False,
                    )
                    .text.strip()
                )
                job['company'] = s.find(
                    'div', attrs={'class', 'jobInfoItem jobEmpolyerName'}
                ).text.strip()
                job['location'] = s.get('data-job-loc')
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
                job['date'] = (
                    s.find('div', attrs={'class', 'jobLabels'})
                    .find('span', attrs={'class', 'jobLabel nowrap'})
                    .text.strip()
                )
            except AttributeError:
                job['date'] = ''

            try:
                part_url = (
                    s.find('div', attrs={'class', 'logoWrap'}).find(
                        'a').get('href')
                )
                job['id'] = s.get('data-id')
                job['link'] = (
                    f'https://www.glassdoor.'
                    f"{self.search_terms['region']['domain']}"
                    f'{part_url}'
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
