"""Scraper designed to get jobs from www.indeed.com / www.indeed.ca
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
#from jobfunnel.config import JobFunnelConfig  # causes a circular import


ID_REGEX = re.compile(r'id=\"sj_([a-zA-Z0-9]*)\"')
MAX_RESULTS_PER_INDEED_PAGE = 50


class BaseIndeedScraper(BaseScraper):
    """Scrapes jobs from www.indeed.X
    """

    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger) -> None:
        """Init that contains indeed specific stuff
        """
        super().__init__(session, config, logger)
        self.max_results_per_page = MAX_RESULTS_PER_INDEED_PAGE
        self.query = '+'.join(self.config.search_config.keywords)

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

        Override this as needed.
        """
        return [
            JobField.TITLE, JobField.COMPANY, JobField.LOCATION,
            JobField.KEY_ID, JobField.TAGS, JobField.POST_DATE,
            # JobField.WAGE, JobField.REMOTE
            # FIXME: wage and remote are available in listings
        ]

    @property
    def job_set_fields(self) -> str:
        """Call self.set(...) for the JobFields in this list when scraping a Job

        NOTE: Since this passes the Job we are updating, the order of this list
        matters if set fields rely on each-other.

        Override this as needed.
        """
        return [JobField.URL, JobField.DESCRIPTION]

    @property
    def delayed_get_set_fields(self) -> str:
        """Delay execution when getting /setting any of these attributes of a
        job.

        Override this as needed.
        """
        return [JobField.DESCRIPTION]

    @property
    def headers(self) -> Dict[str, str]:
        """Session header for indeed.X
        """
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer':
                f'https://www.indeed.{self.config.search_config.domain}/',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from a job source into a list of job-soups

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make Job init
        """
        # Get the search url
        search_url = self._get_search_url()

        # Parse total results, and calculate the # of pages needed
        pages = self._get_num_search_result_pages(search_url)
        self.logger.info(
            f"Found {pages} pages of search results for query={self.query}"
        )

        # Init list of job soups
        job_soup_list = []  # type: List[Any]

        # Init threads & futures list FIXME: use existing ThreadPoolExecutor
        threads = ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS)
        futures_list = []  # FIXME: type?

        # Scrape soups for all the result pages containing lists of jobs found
        for page in range(0, pages):
            futures_list.append(
                threads.submit(
                    self._get_job_soups_from_search_page, search_url, page,
                    job_soup_list
                )
            )

        # Wait for all scrape jobs to finish
        wait(futures_list)

        return job_soup_list

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object by JobField
        """
        if parameter == JobField.TITLE:
            return soup.find(
                'a', attrs={'data-tn-element': 'jobTitle'}
            ).text.strip()
        elif parameter == JobField.COMPANY:
            return soup.find('span', attrs={'class': 'company'}).text.strip()
        elif parameter == JobField.LOCATION:
            return soup.find('span', attrs={'class': 'location'}).text.strip()
        elif parameter == JobField.TAGS:
            # tags may not be on page and that's ok.
            table_soup = soup.find(
                'table', attrs={'class': 'jobCardShelfContainer'}
            )
            if table_soup:
                return [
                    td.text.strip() for td in table_soup.find_all(
                        'td', attrs={'class': 'jobCardShelfItem'}
                    )
                ]
        # elif parameter == JobField.REMOTE:
        # TODO: Impl, this is available in listings as: <span class="remote">...
        # elif parameter == JobField.WAGE:
        # TODO: Impl, this is available as: <span class="salaryText">...
        elif parameter == JobField.POST_DATE:
            return calc_post_date_from_relative_str(
                soup.find('span', attrs={'class': 'date'}).text.strip()
            )
        elif parameter == JobField.KEY_ID:
            return ID_REGEX.findall(
                str(
                    soup.find(
                        'a', attrs={'class': 'sl resultLink save-job-link'}
                    )
                )
            )[0]
        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField
        """
        if parameter == JobField.DESCRIPTION:
            detailed_job_soup = BeautifulSoup(
                self.session.get(job.url).text, self.config.bs4_parser
            )
            job.description = detailed_job_soup.find(
                id='jobDescriptionText'
            ).text.strip()
        elif parameter == JobField.URL:
            job.url = (
                f"http://www.indeed.{self.config.search_config.domain}/"
                f"viewjob?jk={job.key_id}"
            )
        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")

    def _get_search_url(self, method: Optional[str] = 'get') -> str:
        """Get the indeed search url from SearchTerms
        TODO: use Enum for method instead of str.
        """
        if method == 'get':
            # TODO: impl. &remotejob=.... string which allows for remote search
            # i.e &remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11
            return (
                "https://www.indeed.{0}/jobs?q={1}&l={2}%2C+{3}&radius={4}&"
                "limit={5}&filter={6}".format(
                    self.config.search_config.domain,
                    self.query,
                    self.config.search_config.city.replace(' ', '+',),
                    self.config.search_config.province_or_state,
                    self._convert_radius(self.config.search_config.radius),
                    self.max_results_per_page,
                    int(self.config.search_config.return_similar_results)
                )
            )
        elif method == 'post':
            # TODO: implement post style for indeed.X
            raise NotImplementedError()
        else:
            raise ValueError(f'No html method {method} exists')

    def _convert_radius(self, radius: int) -> int:
        """Quantizes the user input radius to a valid radius value into:
        5, 10, 15, 25, 50, 100, and 200 kilometers or miles.
        TODO: implement with numpy instead of if/else cases.
        """
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
        elif radius >= 100:
            radius = 100
        return radius

    def _get_job_soups_from_search_page(self, search: str, page: str,
                                        job_soup_list: List[BeautifulSoup]
                                        ) -> None:
        """Scrapes the indeed page for a list of job soups
        NOTE: modifies the job_soup_list in-place
        """
        url = f'{search}&start={int(page * self.max_results_per_page)}'
        job_soup_list.extend(
            BeautifulSoup(
                self.session.get(url).text, self.config.bs4_parser
            ).find_all('div', attrs={'data-tn-component': 'organicJob'})
        )

    def _get_num_search_result_pages(self, search_url: str, max_pages=0) -> int:
        """Calculates the number of pages of job listings to be scraped.

        i.e. your search yields 230 results at 50 res/page -> 5 pages of jobs

        Args:
			max_pages: the maximum number of pages to be scraped.
        Returns:
            The number of pages to be scraped.
        """
        # Get the html data, initialize bs4 with lxml
        request_html = self.session.get(search_url)
        query_resp = BeautifulSoup(request_html.text, self.config.bs4_parser)
        num_res = query_resp.find(id='searchCountPages').contents[0].strip()
        num_res = int(re.findall(r'f (\d+) ', num_res.replace(',', ''))[0])
        number_of_pages = int(ceil(num_res / self.max_results_per_page))
        if max_pages == 0:
            return number_of_pages
        elif number_of_pages < max_pages:
            return number_of_pages
        else:
            return max_pages


class IndeedScraperCANEng(BaseIndeedScraper, BaseCANEngScraper):
    """Scrapes jobs from www.indeed.ca
    """
    pass

class IndeedScraperUSAEng(BaseIndeedScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.indeed.com
    """
    pass
