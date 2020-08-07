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
#from jobfunnel.config import JobFunnelConfig  FIXME: circular imports issue


# Defaults we use from localization, the scraper can always override it.
DOMAIN_FROM_LOCALE = {
    Locale.CANADA_ENGLISH: 'ca',
    Locale.CANADA_FRENCH: 'ca',
    Locale.USA_ENGLISH: 'com',
}


class BaseScraper(ABC):
    """Base scraper object, for generating List[Job] from a specific job source

    TODO: accept filters: List[Filter] here if we have Filter(ABC)
    NOTE: we want to use filtering here because scraping blurbs can be slow.
    """
    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger) -> None:
        self.session = session
        self.config = config
        self.logger = logger
        self.session.headers.update(self.headers)

    @property
    def domain(self) -> str:
        """Get the domain string from the locale i.e. 'ca'
        NOTE: if you have a special case for your locale (i.e. canadian .com)
        inherit from BaseScraper and set this and locale in your Scraper class
        """
        if not self.locale in DOMAIN_FROM_LOCALE:
            raise ValueError(f"Unknown domain for locale: {self.locale}")
        return DOMAIN_FROM_LOCALE[self.locale]

    @property
    def bs4_parser(self) -> str:
        """Beautiful soup 4's parser setting
        NOTE: it's the same for all scrapers rn so it's not abstract
        """
        return 'lxml'

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
        """
        # Make a dict of job postings from the listing briefs
        jobs_dict = {}  # type: Dict[str, Job]
        for job_soup in self.scrape_job_soups():

            # Key by id to prevent duplicate key_ids FIXME: add a key-warning
            job = self.scrape_job(job_soup)
            jobs_dict[job.key_id] = job

        def _get_with_delay(self, job: Job, delay: float) -> Tuple[Job, str]:
            """Get a job's page by the job url with a delay beforehand
            """
            sleep(delay)
            self.logger.info(
                f'Delay of {delay:.2f}s, getting search results for: {job.url}'
            )
            job_page_soup = BeautifulSoup(
                self.session.get(job.url).text, self.bs4_parser
            )
            return job, job_page_soup

        def _parse(self, job: Job, job_page_soup: BeautifulSoup) -> None:
            """Set job.description
            TODO: roll into our delay callback
            """
            try:
                self.get_short_job_description(job_page_soup)
            except AttributeError:
                self.logger.warning(
                    f"Unable to scrape short description for job {job.key_id}."
                )
            job.clean_strings()

        # Scrape stuff that we are delaying for
        # FIXME: this is hard-coded to delay scraping of descriptions only rn
        # maybe we can just use a queue and calc delays on-the-fly in scrape_job
        threads = ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS)
        jobs_list = list(jobs_dict.values())
        delays = calculate_delays(len(jobs_list), self.config.delay_config)
        delay_threader(
            jobs_list, _get_with_delay, _parse, threads, self.logger, delays
        )

        # FIXME: impl. once CSV supports it, indeed supports it and we make
        # delaying more flexible (i.e. queue)
        # try:
        #     self.get_short_job_description(job_soup)
        # except AttributeError:
        #     self.logger.warning(
        #         f"Unable to scrape short description for job {key_id}."
        #     )

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
        except AttributeError:
            tags = []  # type: List[str]
            self.logger.warning(f"Unable to scrape tags for job {key_id}")

        try:
            post_date = self.get_job_date(job_soup)
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
            short_description='', # We will populate this later per-job-page
            post_date=post_date,
            raw='',  # FIXME: we cannot pickle the soup object (job_soup)
            tags=tags,
        )

        # TODO: make these calls work here, maybe use a queue with delaying?
        # These calls require additional get using job.url
        # try:
        #     self.get_job_description(job, job_soup)
        # except AttributeError:
        #     self.logger.warning(
        #         f"Unable to scrape description for job {key_id}."
        #     )

        # try:
        #     self.get_short_job_description(job_soup)
        # except AttributeError:
        #     self.logger.warning(
        #         f"Unable to scrape short description for job {key_id}."
        #     )

        return job

    # FIXME: review below types and complete docstrings

    @abstractmethod
    def scrape_job_soups(self) -> List[BeautifulSoup]:
        """Generate a list of soups for each job object.
        i.e. the job listing on a search results page.
        NOTE: you can use job soups to get more detailed listings later
        i.e self.get('details_from_job_page') ->  make get request to load desc.
        """
        pass

    # TODO: this might be more elegant:
    # @abstractmethod
    # def get(self, parameter: str,
    #         soup: BeautifulSoup) -> Union[str, List[str], date]:
    #     """Get a single job attribute from a soup object
    #     i.e. get 'description' --> str
    #     """

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
                            job_soup: BeautifulSoup = None) -> None:
        """Parses and stores job description html and sets Job.description
        NOTE: this accepts Job because it allows using other job attributes
        to make new session.get() for job-specific information.
        """
        pass

    @abstractmethod
    def get_short_job_description(self, job: Job,
                                  job_soup: BeautifulSoup = None) -> None:
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

