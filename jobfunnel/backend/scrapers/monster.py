"""Scrapers for www.monster.X
"""
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta
import logging
from math import ceil
from time import sleep, time
from typing import Dict, List, Tuple, Optional, Any
import re
from requests import Session

from bs4 import BeautifulSoup

from jobfunnel.resources import Locale, MAX_CPU_WORKERS, JobField
from jobfunnel.backend import Job, JobStatus
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.backend.scrapers.base import (
    BaseScraper, BaseCANEngScraper, BaseUSAEngScraper
)

MAGIC_MONSTER_SEARCH_STRING = 'skr_navigation_nhpso_searchMain'
MAX_RESULTS_PER_MONSTER_PAGE = 25
ID_REGEX = re.compile(
    r'/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]'
    r'{12})|\d+)'
)


class BaseMonsterScraper(BaseScraper):
    """Scraper for www.monster.X
    """

    def __init__(self, session: Session, config: 'JobFunnelConfig') -> None:
        """Init that contains monster specific stuff
        """
        super().__init__(session, config)
        self.query = '-'.join(
            self.config.search_config.keywords
        ).replace(' ', '-')

    # TODO: implement TAGS

    @property
    def min_required_job_fields(self) -> str:
        """If we dont get() or set() any of these fields, we will raise an
        exception instead of continuing without that information.
        """
        return [
            JobField.TITLE, JobField.COMPANY, JobField.LOCATION,
            JobField.KEY_ID, JobField.URL
        ]

    @property
    def job_get_fields(self) -> str:
        """Call self.get(...) for the JobFields in this list when scraping a Job
        """
        return [
            JobField.TITLE, JobField.COMPANY, JobField.LOCATION,
            JobField.POST_DATE, JobField.URL,
        ]

    @property
    def job_set_fields(self) -> str:
        """Call self.set(...) for the JobFields in this list when scraping a Job
        """
        return [JobField.KEY_ID, JobField.DESCRIPTION]

    @property
    def delayed_get_set_fields(self) -> str:
        """Delay execution when getting /setting any of these attributes of a
        job.

        Override this as needed.
        """
        return [JobField.DESCRIPTION]

    @property
    def headers(self) -> Dict[str, str]:
        """Session header for monster.X
        """
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer':
                f'https://www.monster.{self.config.search_config.domain}/',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object by JobField
        """
        if parameter == JobField.TITLE:
            return soup.find('h2', attrs={'class': 'title'}).text.strip()
        elif parameter == JobField.COMPANY:
            return soup.find('div', attrs={'class': 'company'}).text.strip()
        elif parameter == JobField.LOCATION:
            return soup.find('div', attrs={'class': 'location'}).text.strip()
        elif parameter == JobField.POST_DATE:
            return calc_post_date_from_relative_str(
                soup.find('time').text.strip()
            )
        elif parameter == JobField.URL:
            return str(
                soup.find('a', attrs={'data-bypass': 'true'}).get('href')
            )
        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField
        """
        if parameter == JobField.KEY_ID:
            job.key_id = ID_REGEX.findall(job.url)[0]
        elif parameter == JobField.DESCRIPTION:
            detailed_job_soup = BeautifulSoup(
                self.session.get(job.url).text, self.config.bs4_parser
            )
            job.description = detailed_job_soup.find(
                id='JobDescription'
            ).text.strip()
        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from a job source into a list of job-soups

        TODO: use threading here too

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make Job init
        """
        # Get the search url
        search_url = self._get_search_url()

        # Load our initial search results listings page
        initial_seach_results_html = self.session.get(search_url)
        initial_search_results_soup = BeautifulSoup(
            initial_seach_results_html.text, self.config.bs4_parser
        )

        # Parse total results, and calculate the # of pages needed
        n_pages = self._get_num_search_result_pages(initial_search_results_soup)
        self.logger.info(
            f"Found {n_pages} pages of search results for query={self.query}"
        )

        # Get first page of listing soups from our search results listings page
        job_soups_list = self._get_job_soups_from_search_page(
            initial_search_results_soup
        )

        # Get all the other pages
        for page in range(1, n_pages):
            next_listings_page_soup = BeautifulSoup(
                self.session.get(self._get_results_page_url(page, search_url)),
                self.config.bs4_parser,
            )
            job_soups_list.extend(
                self._get_job_soups_from_search_page(next_listings_page_soup)
            )

        return job_soups_list

    def _get_results_page_url(self, cur_page: int, search_url: str) -> str:
        """Get the next page of search listings
        """
        return f'{search_url}&start={cur_page}'

    def _get_job_soups_from_search_page(self,
                                        initial_results_soup: BeautifulSoup,
                                        ) -> List[BeautifulSoup]:
        """Get individual job listing soups from a results page of many jobs
        """
        return initial_results_soup.find_all('div', attrs={'class': 'flex-row'})

    def _get_num_search_result_pages(self, initial_results_soup: BeautifulSoup,
                                     max_pages=0) -> int:
        """Calculates the number of pages of job listings to be scraped.

        i.e. your search yields 230 results at 50 res/page -> 5 pages of jobs

        Args:
            initial_results_soup: the soup for the first search results page
			max_pages: the maximum number of pages to be scraped.
        Returns:
            The number of pages of job listings to be scraped.
        """
        # scrape total number of results, and calculate the # pages needed
        partial = initial_results_soup.find('h2', 'figure').text.strip()
        assert partial, "Unable to identify number of search results"
        num_res = int(re.findall(r'(\d+)', partial)[0])
        return int(ceil(num_res / MAX_RESULTS_PER_MONSTER_PAGE))

    def _get_search_url(self, method: Optional[str] = 'get') -> str:
        """Get the monster search url from SearchTerms
        TODO: use Enum for method instead of str.
        TODO: implement POST
        """
        if method == 'get':
            return (
                'https://www.monster.{0}/jobs/search/?q={1}&where={2}__2C-{3}'
                    '&intcid={4}&rad={5}&where={2}__2c-{3}'.format(
                    self.config.search_config.domain,
                    self.query,
                    self.config.search_config.city.replace(' ', '-'),
                    self.config.search_config.province_or_state,
                    MAGIC_MONSTER_SEARCH_STRING,
                    self._convert_radius(self.config.search_config.radius)
                )
            )
        elif method == 'post':
            raise NotImplementedError()
        else:
            raise ValueError(f'No html method {method} exists')

    @abstractmethod
    def _convert_radius(self, radius: int) -> int:
        """NOTE: radius conversion is units/locale specific
        """
        pass

class MonsterScraperCANEng(BaseMonsterScraper, BaseCANEngScraper):
    """Scrapes jobs from www.monster.ca
    """
    def _convert_radius(self, radius: int) -> int:
        """convert radius in miles TODO replace with numpy
        """
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


class MonsterScraperUSAEng(BaseMonsterScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.monster.com
    """

    def _convert_radius(self, radius: int) -> int:
        """convert radius in miles TODO replace with numpy
        """
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
        return radius
