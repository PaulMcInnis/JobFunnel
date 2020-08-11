"""The base scraper class to be used for all web-scraping emitting Job objects
"""
import datetime
import logging
import os
import random
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep, time
from typing import Any, Dict, List, Tuple, Union

from bs4 import BeautifulSoup
from requests import Session
from tqdm import tqdm

from jobfunnel.backend import Job, JobStatus
from jobfunnel.backend.tools.delay import calculate_delays
from jobfunnel.resources import (MAX_CPU_WORKERS, USER_AGENT_LIST, JobField,
                                 Locale)
# from jobfunnel.config import JobFunnelConfig  FIXME: circular imports issue


class BaseScraper(ABC):
    """Base scraper object, for scraping and filtering Jobs from a provider
    """
    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger) -> None:
        self.session = session
        self.config = config
        self.logger = logger
        if self.headers:
            self.session.headers.update(self.headers)

        # Ensure that the locale we want to use matches the locale that the
        # scraper was written to scrape in:
        if self.config.search_config.locale != self.locale:
            raise ValueError(
                f"Attempting to use scraper designed for {self.locale.name} "
                "when config indicates user is searching with "
                f"{self.config.search_config.locale.name}"
            )

        # Ensure our properties satisfy constraints
        self._validate_get_set()

        # Init a thread executor (multi-worker) TODO: can't reuse after shutdown
        self.executor = ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS)

    @property
    def user_agent(self) -> str:
        """Get a user agent for this scraper
        """
        return random.choice(USER_AGENT_LIST)

    @property
    def min_required_job_fields(self) -> str:
        """If we dont get() or set() any of these fields, we will raise an
        exception instead of continuing without that information.

        NOTE: pointless to check for locale / provider / other defaults

        Override this as needed.
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
    @abstractmethod
    def locale(self) -> Locale:
        """The localization that this scraper was built for.

        We will use this to put the right filters & scrapers together

        NOTE: it is best to inherit this from Base<Locale>Class (btm. of file)
        """
        pass

    @property
    @abstractmethod
    def headers(self) -> Dict[str, str]:
        """The Session headers for this scraper to be used with
        requests.Session.headers.update()
        """
        pass

    def scrape(self) -> Dict[str, Job]:
        """Scrape job source into a dict of unique jobs keyed by ID

        NOTE: respectfully delays for scraping of configured job attributes in
        self.

        Returns:
            jobs (Dict[str, Job]): list of Jobs in a Dict keyed by job.key_id
        """

        # Get a list of job soups from the initial search results page
        try:
            job_soups = self.get_job_soups_from_search_result_listings()
        except Exception as err:
            raise ValueError(
                "Unable to extract jobs from initial search result page:\n\t"
                f"{str(err)}"
            )
        n_soups = len(job_soups)
        self.logger.info(
            f"Scraped {n_soups} job listings from search results pages"
        )

        # Calculate delays for get/set calls per-job NOTE: only get/set
        # calls in self.delayed_get_set_fields will be delayed.
        delays = calculate_delays(n_soups, self.config.delay_config)
        results = []
        for job_soup, delay in zip(job_soups, delays):
            results.append(
                self.executor.submit(
                    self.scrape_job, job_soup=job_soup, delay=delay
                )
            )

        # Loops through futures as completed and removes each if successfully parsed
        # For each job-soup object, scrape the soup into a Job  (w/o desc.)
        jobs_dict = {}  # type: Dict[str, Job]
        for future in tqdm(as_completed(results), total=n_soups):
            job = future.result()
            if job.key_id in jobs_dict:
                self.logger.error(
                    f"Job {job.title} and {jobs_dict[job.key_id].title} share "
                    f"duplicate key_id: {job.key_id}"
                )
            jobs_dict[job.key_id] = job

        # Cleanup + log
        self.executor.shutdown()

        return jobs_dict

    def scrape_job(self, job_soup: BeautifulSoup, delay: float) -> Job:
        """Scrapes a search page and get a list of soups that will yield jobs
        Arguments:
            job_soup [BeautifulSoup]: This is a soup object that your get/set
                will use to perform the get/set action. It should be specific
                to this job and not contain other job information.
            delay [float]: how long to delay getting/setting for certain
                get/set calls while scraping data for this job.

        Returns:
            Job: job object constructed from the soup and localization of class
        """
        # Init kwargs
        job_init_kwargs = {
            JobField.STATUS: JobStatus.NEW,
            JobField.LOCALE: self.locale,
            JobField.QUERY: self.config.search_config.query_string,
            JobField.DESCRIPTION: '',
            JobField.URL: '',
            JobField.SHORT_DESCRIPTION: '',  # TODO: impl.
            JobField.RAW: '',  # TODO: impl.
            JobField.PROVIDER: self.__class__.__name__,
        }  # type: Dict[JobField, Any]

        # Formulate the get/set actions
        actions_list = [(True, f) for f in self.job_get_fields]
        actions_list += [(False, f) for f in self.job_set_fields]

        # Scrape the data for the post, requiring a minimum of info...
        job = None  # type: Union[None, Job]
        for is_get, field in actions_list:

            # Respectfully delay if it's configured to do so.
            if field in self.delayed_get_set_fields:
                sleep(delay)

            kwarg_name = field.name.lower()
            try:
                if is_get:
                    job_init_kwargs[field] = self.get(field, job_soup)
                else:
                    if not job:
                        # Build initial job object + populate all the job
                        job = Job(**{
                            k.name.lower(): v for k, v
                            in job_init_kwargs.items()
                        })
                    self.set(field, job, job_soup)
            except Exception as err:
                if field in self.min_required_job_fields:
                    raise ValueError(
                        "Unable to scrape minimum-required job field: "
                        f"{field.name} Got error:{str(err)}"
                    )
                else:
                    self.logger.warning(
                        "Unable to scrape {} for job{}:\n\t{}".format(
                            kwarg_name, ' ' + job.url if job else '', str(err)
                        )
                    )

        assert job, "Failed to initialize job"  # NOTE: should never see this
        job.validate()

        return job

    @abstractmethod
    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes a job provider's response to a search query where we are
        shown many job listings at once.

        NOTE: the soups list returned by this method should contain enough
        information to set your self.min_required_job_fields with get/set.

        NOTE: for situations where the data you want is in the job's own page
        and we need to make another get request, handle those in set()
        and make a request using job.url (it will be respectfully delayed)

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make a Job
        """
        pass

    @abstractmethod
    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object by JobField

        i.e. if param is JobField.COMPANY --> scrape from soup --> return str
        TODO: better way to handle ret type than a massive Union?
        """
        pass

    @abstractmethod
    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField

        NOTE: (remember) do not return anything in here! it sets job attribs

        Use this to set Job attribs that rely on Job existing already
        with the required minimum fields (i.e. you can set description by
        getting the job's detail page with job.url)
        """
        pass


    def _validate_get_set(self) -> None:
        """Ensure the get/set actions cover all need attribs and dont intersect
        """
        set_job_get_fields = set(self.job_get_fields)
        set_job_set_fields = set(self.job_set_fields)
        all_set_get_fields = set(self.job_get_fields + self.job_set_fields)
        set_min_fields = set(self.min_required_job_fields)

        set_missing_req_fields = set_min_fields - all_set_get_fields
        if set_missing_req_fields:
            raise ValueError(
                f"Job attributes: {set_missing_req_fields} are required and not"
                f" implemented by {self.__class__.__name__}"
            )

        field_intersection = set_job_get_fields.intersection(set_job_set_fields)
        if field_intersection:
            raise ValueError(
                f"Job attributes: {field_intersection} are implemented by both"
                f"get() and set() methods of {self.__class__.__name__}"
            )
        for field in JobField:
            # NOTE: we exclude status, locale, query, provider and scrape date
            # because these are set without needing any scrape data.
            # TODO: SHORT and RAW are not impl. rn. remove this check when impl.
            if (field not in [JobField.STATUS, JobField.LOCALE, JobField.QUERY,
                              JobField.SCRAPE_DATE, JobField.PROVIDER,
                              JobField.SHORT_DESCRIPTION, JobField.RAW]
                    and field not in self.job_get_fields
                    and field not in self.job_set_fields):
                self.logger.warning(
                    f"No get() or set() will be done for Job attr: {field.name}"
                )

# Just some basic localized scrapers, you can inherit these to set the locale.

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
        return Locale.CANADA_ENGLISH
