"""
"""
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
import logging
import math
from requests import post, Session
import re
from typing import Dict, List, Tuple, Optional
import time

from jobfunnel.backend import Job
from jobfunnel.backend.localization import Locale
from jobfunnel.backend.scrapers import BaseCANEngScraper, BaseUSAEngScraper
from jobfunnel.backend.scrapers.glassdoor.base import GlassDoorBase


class GlassDoorStatic(GlassDoorBase):
    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger):
        pass
#         """Init
#         """
#         super().__init__(session, config, logger)
#         # Concatenates keywords with '-'
#         self.query_string = ' '.join(self.config.search_terms.keywords)

#     def search_page_for_job_soups(self, page: str, url: str,
#                                   job_soup_list: List[BeautifulSoup]) -> None:
#         """Scrapes the glassdoor page for a list of job soups
#         TODO: document
#         """
#         self.logger.info(f'Getting glassdoor page {page} : {url}')
#         job = BeautifulSoup(
#             self.session.get(url).text, self.bs4_parser
#         ).find_all('li', attrs={'class', 'jl'})
#         job_soup_list.extend(job)

#     def set_description(self, job: Job) -> None:
#         """Scrapes the glassdoor job link for the description
#         TODO: document
#         """
#         self.logger.info(f'Getting glassdoor search: {job.url}')
#         job_link_soup = BeautifulSoup(
#             self.session.get(job.url).text, self.bs4_parser
#         )
#         try:
#             job.description = job_link_soup.find(
#                 id='JobDescriptionContainer'
#             ).text.strip()
#             job.clean_strings()
#         except AttributeError:
#             self.logger.error(f"Unable to scrape description for: {job.url}")
#             job.description = ''

#     def get_description_with_delay(self, job: Job,
#                                    delay: float) -> Tuple[Job, str]:
#         """Gets description from glassdoor job link with a request delay
#         NOTE: this is per-job
#         """
#         time.sleep(delay)
#         self.logger.info(
#             f'Delay of {delay:.2f}s, getting glassdoor search: {job.url}'
#         )
#         return job, self.session.get(job.url).text

#     def get_num_pages(self, soup_base: BeautifulSoup) -> int:
#         """Scrape total number of results, and calculate the # pages needed
#         """
#         num_res = soup_base.find(
#             'p', attrs={'class', 'jobsCount'}).text.strip()
#         num_res = int(re.findall(r'(\d+)', num_res.replace(',', ''))[0])
#         self.logger.info(
#             f"Found {num_res} glassdoor results for query='{self.query_string}'"
#         )
#         return int(math.ceil(num_res / self.max_results_per_page))

#     def get_page_url(self, soup_base: BeautifulSoup) -> str:
#         """Get the next page URL
#         """
#         # Gets partial url for next page
#         partial_url = soup_base.find(
#             'li', attrs={'class', 'next'}
#         ).find('a').get('href')

#         # Uses partial url to construct next page url
#         page_url = re.sub(
#             r'_IP\d+\.',
#             f'_IP{page}.',
#             f"https://www.glassdoor.{self.domain}{partial_url}",
#         )

#     def get_job_title(self, soup: BeautifulSoup) -> str:
#         """Get the title from page soup
#         """
#         return soup.find(
#             'div', attrs={'class', 'jobContainer'}
#         ).find(
#             'a',
#             attrs={'class', 'jobLink jobInfoItem jobTitle'},
#             recursive=False,
#         ).text.strip()

#     def get_job_company(self, soup: BeautifulSoup) -> str:
#         """Get the company name from page soup
#         """
#         return soup.find(
#             'div', attrs={'class', 'jobInfoItem jobEmpolyerName'}
#         ).text.strip()

#     def get_job_location(self, soup: BeautifulSoup) -> str:
#         """Get job location from page soup
#         """
#         return soup.get('data-job-loc')

#     def get_job_tags(self, soup: BeautifulSoup) -> List[str]:
#         """Get tags metadata from page soup
#         """
#         labels = soup.find_all('div', attrs={'class', 'jobLabel'})
#         return [l.text.strip() for l in labels if l.text.strip() != 'New']

#     def scrape(self) -> Dict[str, Job]:
#         """Scrapes job posting from glassdoor and pickles it
#         """
#         # Get the search url and data
#         search, data = self.get_search_url(method='post')

#         # Get the html data
#         request_html = self.session.post(search, data=data)

#         # Create the soup from our overall search request
#         soup_base = BeautifulSoup(request_html.text, self.bs4_parser)
#         num_pages = self.get_num_pages(soup_base)

#         # Init list of job soups, threads and a list to populate
#         threads = ThreadPoolExecutor(max_workers=8)
#         job_soup_list = []  # type: List[BeautifulSoup]
#         fts = []  # FIXME: type?

#         # Search the pages to extract the list of job soups
#         for page in range(1, num_pages + 1):
#             if page == 1:
#                 fts.append(
#                     threads.submit(
#                         self.search_page_for_job_soups,
#                         page,
#                         request_html.url,
#                         job_soup_list,
#                     )
#                 )
#             else:
#                 page_url = self.get_page_url(soup_base)
#                 fts.append(
#                     threads.submit(
#                         self.search_page_for_job_soups,
#                         page,
#                         page_url,
#                         job_soup_list,
#                     )
#                 )
#         # Wait for all scrape jobs to finish
#         wait(fts)

#         # Get the job data from brief listings
#         jobs_dict = {}  # type: Dict[str, Job]
#         for soup in job_soup_list:

#             status = JobStatus.NEW
#             title, company, location, tags = None, None, None, []
#             post_date, key_id, url, short_description = None, None, None, None

#             try:
#                 # Min. required scraping data
#                 title = self.get_job_title(soup)
#                 company = self.get_job_company(soup)
#                 location = self.get_job_location(soup)
#             except AttributeError:
#                 self.logger.error("Unable to scrape minimum-required job info!")
#                 continue

#             try:
#                 tags = self.get_job_tags(soup)
#             except AttributeError:
#                 self.logger.warning(f"Unable to scrape job tags for {key_id}")

#             try:
#                 job['date'] = (
#                     soup.find('div', attrs={'class', 'jobLabels'})
#                     .find('span', attrs={'class', 'jobLabel nowrap'})
#                     .text.strip()
#                 )
#             except AttributeError:
#                 job['date'] = ''

#             try:
#                 part_url = (
#                     soup.find('div', attrs={'class', 'logoWrap'}).find(
#                         'a').get('href')
#                 )
#                 job['id'] = soup.get('data-id')
#                 job['link'] = (
#                     f'https://www.glassdoor.'
#                     f"{self.search_terms['region']['domain']}"
#                     f'{part_url}'
#                 )

#             except (AttributeError, IndexError):
#                 job['id'] = ''
#                 job['link'] = ''

#             job['query'] = self.query
#             job['provider'] = self.provider

#             # key by id
#             self.scrape_data[str(job['id'])] = job


#             job = Job(
#                 title=title,
#                 company=company,v
#                 location=location,
#                 description='',  # We will populate this later per-job-page
#                 key_id=key_id,
#                 url=url,
#                 locale=self.locale,
#                 query=self.query,
#                 status=status,
#                 provider='indeed',  # FIXME: we should inherit this
#                 short_description=short_description,
#                 post_date=post_date,
#                 raw='',  # FIXME: we cannot pickle the soup object (s)
#                 tags=tags,
#             )

#         # Do not change the order of the next three statements if you want date_filter to work

#         # stores references to jobs in list to be used in blurb retrieval
#         scrape_list = [i for i in self.scrape_data.values()]
#         # converts job date formats into a standard date format
#         post_date_from_relative_post_age(scrape_list)
#         # apply job pre-filter before scraping blurbs
#         super().pre_filter(self.scrape_data, self.provider)

#         # checks if delay is set or not, then extracts blurbs from job links
#         if self.delay_config is not None:
#             # calls super class to run delay specific threading logic
#             super().delay_threader(
#                 scrape_list, self.get_description_with_delay, self.parse_blurb, threads
#             )

#         else:  # maps jobs to threads and cleans them up when done
#             # start time recording
#             start = time()

#             # maps jobs to threads and cleans them up when done
#             threads.map(self.set_description, scrape_list)
#             threads.shutdown()

#             # end and print recorded time
#             end = time()
#             print(f'{self.provider} scrape job took {(end - start):.3f}s')



# These are the same exact logic, same website beyond the domain.
class GlassDoorStaticCAEng(GlassDoorStatic, BaseCANEngScraper):
    pass


class GlassDoorStaticUSAEng(GlassDoorStatic, BaseUSAEngScraper):
    pass
