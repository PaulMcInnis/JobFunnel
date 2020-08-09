"""The base scraper class to be used for all web-scraping emitting Job objects
"""
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait
import datetime
import logging
import os
from time import sleep, time
from typing import Dict, List, Tuple
import random
from requests import Session

from jobfunnel.resources import USER_AGENT_LIST, Locale, MAX_CPU_WORKERS
from jobfunnel.backend.tools.delay import calculate_delays, delay_threader
from jobfunnel.backend import Job, JobStatus
# from jobfunnel.config import JobFunnelConfig  FIXME: circular imports issue


class BaseScraper(ABC):
    """Base scraper object, for generating List[Job] from a specific job source

    TODO: accept filters: List[Filter] here if we have Filter(ABC)
    NOTE: we want to use filtering here because scraping blurbs can be slow.
    NOTE: we don't have domain as an attrib because multiple domains can belong
    to multiple locales. The Locale is intended to define the format of the
    website, the scraping logic needed and the language used - as such,
    SearchConfig is what defines the domain (it is being requested).
    """
    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger) -> None:
        self.session = session
        self.config = config
        self.logger = logger
        if self.headers:
            self.session.headers.update(self.headers)

    @property
    def user_agent(self) -> str:
        """Get a user agent for this scraper
        """
        return random.choice(USER_AGENT_LIST)

    @property
    @abstractmethod
    def locale(self) -> Locale:
        """Get the localizations that this scraper was built for
        We will use this to put the right filters & scrapers together
        NOTE: it is best to inherit this from Base<Locale>Class
        NOTE: self.config.search.locale == self.locale should be true
        """
        pass

    @property
    @abstractmethod
    def headers(self) -> Dict[str, str]:
        """Get the Session headers for this scraper to be used with
        requests.Session.headers.update()
        """
        pass

    def scrape(self) -> Dict[str, Job]:
        """Scrape job source into a dict of unique jobs keyed by ID

        FIXME: this is hard-coded to delay scraping of descriptions only rn
        maybe we can just use a queue and calc delays on-the-fly in scrape_job
        for all session.get requests?
        """
        # Get a list of job soups from the initial search results page
        try:
            job_soups = self.get_job_listings_from_search_results()
        except Exception as err:
            raise ValueError(
                "Unable to extract jobs from initial search result page:\n"
                f"{str(err)}"
            )
        self.logger.info(
            f"Scraped {len(job_soups)} job listings from search results pages"
        )

        # For each job-soup object, scrape the soup into a Job  (w/o desc.)
        jobs_dict = {}  # type: Dict[str, Job]
        for job_soup in job_soups:
            job = self.scrape_job(job_soup)
            if job.key_id in jobs_dict:
                self.logger.error(
                    f"Job {job.title} and {jobs_dict[job.key_id].title} share "
                    f"duplicate key_id: {job.key_id}"
                )
            jobs_dict[job.key_id] = job

        # FIXME: get rid of these two _methods and replace with more flexible
        # delaying implementation.
        def _get_with_delay(job: Job, delay: float) -> Tuple[Job, str]:
            """Get a job's page by the job url with a delay beforehand
            """
            sleep(delay)
            self.logger.info(
                f'Delay of {delay:.1f}s, getting search results for: {job.url}'
            )
            job_page_soup = BeautifulSoup(
                self.session.get(job.url).text, self.config.bs4_parser
            )
            return job, job_page_soup

        def _parse(job: Job, job_page_soup: BeautifulSoup) -> None:
            """Set job.description with the job's own page.
            TODO: move this into our delay callback
            """
            try:
                job.description = self.get_job_description(job, job_page_soup)
            except AttributeError:
                self.logger.warning(
                    f"Unable to scrape short description for job {job.key_id}."
                )
            job.clean_strings()

        # Scrape stuff that we are delaying for
        threads = ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS)
        jobs_list = list(jobs_dict.values())
        delays = calculate_delays(len(jobs_list), self.config.delay_config)
        delay_threader(
            jobs_list, _get_with_delay, _parse, threads, self.logger, delays
        )
        return jobs_dict

    def scrape_job(self, job_soup: BeautifulSoup) -> Job:
        """Scrapes a search page and get a list of soups that will yield jobs

        NOTE: does not currently scrape anything that

        Returns:
            Job: job object constructed from the soup and localization of class
        """
        # Scrape the data for the post, requiring a minimum of info...
        try:
            # Jobs should at minimum have a title, company and location
            title = self.get_job_title(job_soup)
            company = self.get_job_company(job_soup)
            location = self.get_job_location(job_soup)
            key_id = self.get_job_key_id(job_soup)
            url = self.get_job_url(key_id)
        except Exception as err:
            # TODO: decide how we should handle these, proceed or exit?
            raise ValueError(
                "Unable to scrape minimum-required job info!\nerror:" + str(err)
            )

        # Scrape the optional stuff
        try:
            tags = self.get_job_tags(job_soup)
        except AttributeError as err:
            tags = []  # type: List[str]
            self.logger.warning(
                f"Unable to scrape tags for job {key_id}:\n{str(err)}"
            )

        try:
            post_date = self.get_job_post_date(job_soup)
        except (AttributeError, ValueError):
            post_date = datetime.datetime.now()
            self.logger.warning(
                f"Unknown date for job {key_id}, setting to datetime.now()."
            )

        # Init a new job from scraped data
        job = Job(
            title=title,
            company=company,
            location=location,
            description='',  # We will populate this later per-job-page
            key_id=key_id,
            url=url,
            locale=self.locale,
            query='', #self.query_string, FIXME
            status=JobStatus.NEW,
            provider='', #self.__class___.__name__, FIXME
            short_description='', # TODO: impl.
            post_date=post_date,
            raw='',  # FIXME: we cannot pickle the soup object (job_soup)
            tags=tags,
        )

        return job

    # FIXME: review below types and complete docstrings

    # TODO: implement getters like this so we can make the entire thing more
    # flexible.
    # @abstractmethod
    # def get(self, parameter: str,
    #         soup: BeautifulSoup) -> Union[str, List[str], date]:
    #     """Get a single job attribute from a soup object
    #     i.e. get 'description' --> str
    #     """

    @abstractmethod
    def get_job_listings_from_search_results(self) -> List[BeautifulSoup]:
        """Generate a list of soups for each job object from the response to our
        job search query.

        NOTE: This should be in a format where there are many jobs shown to the
        user to click-into in a single view.

        Returns a list of soup objects which correspond to each job shown on the
        results page.
        """
        pass

    @abstractmethod
    def get_job_url(self, job_soup: BeautifulSoup) -> str:
        """Get job url from a job soup
        Args:
			job_soup: BeautifulSoup base to scrape the title from.
        Returns:
            Title of the job (i.e. 'Secret Shopper')
        """
        pass

    @abstractmethod
    def get_job_title(self, job_soup: BeautifulSoup) -> str:
        """Get job title from soup
        Args:
			job_soup: BeautifulSoup base to scrape the title from.
        Returns:
            Title of the job (i.e. 'Secret Shopper')
        """
        pass

    @abstractmethod
    def get_job_company(self, job_soup: BeautifulSoup) -> str:
        """Get job company name from soup
        Args:
			job_soup: BeautifulSoup base to scrape the company from.
        Returns:
            Company name (i.e. 'Aperture Science')
        """
        pass

    @abstractmethod
    def get_job_location(self, job_soup: BeautifulSoup) -> str:
        """Get job location string
        TODO: we should have a better format than str for this.
        """
        pass

    @abstractmethod
    def get_job_tags(self, job_soup: BeautifulSoup) -> List[str]:
        """Fetches the job tags / keywords from a BeautifulSoup base.
        """
        pass

    @abstractmethod
    def get_job_post_date(self, job_soup: BeautifulSoup) -> datetime.date:
        """Fetches the job date from a BeautifulSoup base.
        Args:
			soup: BeautifulSoup base to scrape the date from.
        Returns:
            date of the job's posting
        """
        pass

    @abstractmethod
    def get_job_key_id(self, job_soup: BeautifulSoup) -> str:
        """Fetches the job id from a BeautifulSoup base.
        NOTE: this should be unique, but we should probably use our own SHA
        Args:
			soup: BeautifulSoup base to scrape the id from.
        Returns:
            The job id scraped from soup.
            Note that this function may throw an AttributeError if it cannot
            find the id. The caller is expected to handle this exception.
        """
        pass

    # FIXME: do we want all of these to take in a Job object? might be useful?
    # ... the first in the chain would have job = None for its call though...
    @abstractmethod
    def get_job_description(self, job: Job,
                            job_soup: BeautifulSoup = None) -> str:
        """Parses and stores job description html and sets Job.description
        NOTE: this accepts Job because it allows using other job attributes
        to make new session.get() for job-specific information.
        """
        pass

    @abstractmethod
    def get_short_job_description(self, job: Job,
                                  job_soup: BeautifulSoup = None) -> str:
        """Parses and stores job description from a job's page HTML
        NOTE: this accepts Hob because it allows using other job attributes
        to make new session.get() for job-specific information.
        """
        pass


# Just some basic localized scrapers, can inherit these to set locale as well.

class BaseUSAEngScraper(BaseScraper):
    """Localized scraper for USA English
    """
    @property
    def locale(self) -> Locale:
        return Locale.USA_ENGLISH


class BaseCANEngScraper(BaseScraper):
    """Localized scraper for Canada English
    """
    @property
    def locale(self) -> Locale:
        return Locale.USA_ENGLISH

