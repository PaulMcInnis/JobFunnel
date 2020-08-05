"""
"""
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
import logging
from requests import post, Session
import re
from typing import Dict, List, Tuple, Optional
import time

from jobfunnel.backend import Job
from jobfunnel.backend.localization import Locale, get_domain_from_locale
from jobfunnel.backend.scrapers.glassdoor.base import GlassDoorBase


class GlassDoorStatic(GlassDoorBase):
    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger):
        """Init
        """
        super().__init__(session, config, logger)
        # Sets headers as default on Session object
        self.session.headers.update(self.headers)
        # Concatenates keywords with '-'
        self.query_string = ' '.join(self.search_terms['keywords'])

    def search_page_for_job_soups(self, page, url, job_soup_list) -> None:
        """Scrapes the glassdoor page for a list of job soups
        TODO: document
        """
        self.logger.info(f'Getting glassdoor page {page} : {url}')
        job = BeautifulSoup(
            self.session.get(url).text, self.bs4_parser
        ).find_all('li', attrs={'class', 'jl'})
        job_soup_list.extend(job)

    def set_description(self, job: Job) -> None:
        """Scrapes the glassdoor job link for the description
        TODO: document
        """
        self.logger.info(f'Getting glassdoor search: {job.url}')
        job_link_soup = BeautifulSoup(
            self.session.get(job.url).text, self.bs4_parser
        )
        try:
            job.description = job_link_soup.find(
                id='JobDescriptionContainer'
            ).text.strip()
            job.clean_strings()
        except AttributeError:
            self.logger.error(f"Unable to scrape description for: {job.url}")
            job.description = ''

    def get_description_with_delay(self, job: Job,
                                   delay: float) -> Tuple[Job, str]:
        """Gets description from glassdoor job link with a request delay
        NOTE: this is per-job
        """
        time.sleep(delay)
        self.logger.info(
            f'Delay of {delay:.2f}s, getting glassdoor search: {job.url}'
        )
        return job, self.session.get(job.url).text

    def scrape(self) -> Dict[str, Job]:
        """Scrapes job posting from glassdoor and pickles it
        """
        # Get the search url and data
        search, data = self.get_search_url(method='post')

        # Get the html data
        request_html = self.session.post(search, data=data)

        # Create the soup base
        soup_base = BeautifulSoup(request_html.text, self.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_res = soup_base.find(
            'p', attrs={'class', 'jobsCount'}).text.strip()
        num_res = int(re.findall(r'(\d+)', num_res.replace(',', ''))[0])
        self.logger.info(
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
                scrape_list, self.get_description_with_delay, self.parse_blurb, threads
            )

        else:  # maps jobs to threads and cleans them up when done
            # start time recording
            start = time()

            # maps jobs to threads and cleans them up when done
            threads.map(self.set_description, scrape_list)
            threads.shutdown()

            # end and print recorded time
            end = time()
            print(f'{self.provider} scrape job took {(end - start):.3f}s')



class GlassDoorStaticCAEng(GlassDoorStatic):

    @property
    def locale(self) -> Locale:
        """Get the localizations that this scraper was built for
        We will use this to put the right filters & scrapers together
        """
        return Locale.CANADA_ENGLISH

    @property
    def headers(self) -> Dict[str, str]:
        return{
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                get_domain_from_locale(self.locale)
            ),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }


class GlassDoorStaticUSAEng(GlassDoorStatic):

    @property
    def locale(self) -> Locale:
        """Get the localizations that this scraper was built for
        We will use this to put the right filters & scrapers together
        """
        return Locale.CANADA_ENGLISH

    @property
    def headers(self) -> Dict[str, str]:
        return{
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                get_domain_from_locale(self.locale)
            ),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }