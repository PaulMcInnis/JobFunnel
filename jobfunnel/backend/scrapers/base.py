"""The base scraper class to be used for all web-scraping emitting Job objects
"""
import logging
import os
import random
import sys
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep, time
from typing import Any, Dict, List, Tuple, Union, Optional

from bs4 import BeautifulSoup
from requests import Session
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tqdm import tqdm

from jobfunnel.backend import Job, JobStatus
from jobfunnel.backend.tools.delay import calculate_delays
from jobfunnel.backend.tools import get_logger
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.resources import (MAX_CPU_WORKERS, USER_AGENT_LIST, JobField,
                                 Locale)


if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.config import JobFunnelConfigManager



class BaseScraper(ABC):
    """Base scraper object, for scraping and filtering Jobs from a provider
    """
    def __init__(self, session: Session, config: 'JobFunnelConfigManager',
                 job_filter: JobFilter) -> None:
        """Init

        TODO: we should have a way of establishing pre-requsites for set()

        Args:
            session (Session): session object used to make post and get requests
            config (JobFunnelConfigManager): config containing all needed paths,
                search proxy, delaying and other metadata.
            job_filter (JobFilter): filtering class used to perform on-the-fly
                filtering of jobs to reduce the number of delayed get or set
                (i.e. operations that make requests).

        Raises:
            ValueError: if no Locale is configured in the JobFunnelConfigManager
        """
        self.job_filter = job_filter  # We will use this for live-filtering
        self.session = session
        self.config = config
        self.logger = get_logger(
            self.__class__.__name__,
            self.config.log_level,
            self.config.log_file,
            f"[%(asctime)s] [%(levelname)s] {self.__class__.__name__}: "
            "%(message)s"
        )
        if self.headers:
            self.session.headers.update(self.headers)

        # Elongate the retries TODO: make configurable
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

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
    def job_init_kwargs(self) -> Dict[JobField, Any]:
        """This is a helper property that stores a Dict of JobField : value that
        we set defaults for when scraping. If the scraper fails to get/set these
        we can fail back to the empty value from here.

        i.e. JobField.POST_DATE defaults to today.
        TODO: formalize the defaults for JobFields via Job.__init__(Jobfields...
        """
        return {
            JobField.STATUS: JobStatus.NEW,
            JobField.LOCALE: self.locale,
            JobField.QUERY: self.config.search_config.query_string,
            JobField.DESCRIPTION: '',
            JobField.URL: '',
            JobField.SHORT_DESCRIPTION: '',
            JobField.RAW: None,
            JobField.PROVIDER: self.__class__.__name__,
            JobField.REMOTE: '',
            JobField.WAGE: '',
        }

    @property
    def min_required_job_fields(self) -> List[JobField]:
        """If we dont get() or set() any of these fields, we will raise an
        exception instead of continuing without that information.

        NOTE: pointless to check for locale / provider / other defaults

        Override if needed, but be aware that key_id should always be populated
        along with URL or the user can do nothing with the result.
        """
        return [
            JobField.TITLE, JobField.COMPANY, JobField.LOCATION,
            JobField.KEY_ID, JobField.URL
        ]

    @property
    @abstractmethod
    def job_get_fields(self) -> List[JobField]:
        """Call self.get(...) for the JobFields in this list when scraping a Job.

        NOTE: these will be passed job listing soups, if you have data you need
        to populate that exists in the Job.RAW (the soup from the listing's own
        page), you should use job_set_fields.
        """
        pass

    @property
    @abstractmethod
    def job_set_fields(self) -> List[JobField]:
        """Call self.set(...) for the JobFields in this list when scraping a Job

        NOTE: You should generally set the job's own page as soup to RAW first
        and then populate other fields from this soup, or from each-other here.
        """
        pass

    @property
    @abstractmethod
    def delayed_get_set_fields(self) -> List[JobField]:
        """Delay execution when getting /setting any of these attributes of a
        job.
        """
        pass

    @property
    def high_priority_get_set_fields(self) -> List[JobField]:
        """These get() and/or set() fields will be populated first.

        i.e we need the RAW populated before DESCRIPTION, so RAW should be high.
        i.e. we need to get key_id before we set job.url, so key_id is high.

        NOTE: override as needed.
        """
        return []

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

        FIXME: we need to accept some kind of filter bank argument
            here so we can abort scraping that isn't promising with a minimal
            number of delayed get/sets

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

        # Loops through futures as completed and removes if successfully parsed
        # For each job-soup object, scrape the soup into a Job  (w/o desc.)
        jobs_dict = {}  # type: Dict[str, Job]
        for future in tqdm(as_completed(results), total=n_soups):
            job = future.result()
            if job:
                # Handle duplicates that exist within the scraped data itself.
                # NOTE: if you see alot of these our scrape for key_id is bad
                if job.key_id in jobs_dict:
                    self.logger.error(
                        f"Job {job.title} and {jobs_dict[job.key_id].title} "
                        f"share duplicate key_id: {job.key_id}"
                    )
                jobs_dict[job.key_id] = job

        # Cleanup + log
        self.executor.shutdown()

        return jobs_dict

    def scrape_job(self, job_soup: BeautifulSoup, delay: float
                   ) -> Optional[Job]:
        """Scrapes a search page and get a list of soups that will yield jobs
        Arguments:
            job_soup [BeautifulSoup]: This is a soup object that your get/set
                will use to perform the get/set action. It should be specific
                to this job and not contain other job information.
            delay [float]: how long to delay getting/setting for certain
                get/set calls while scraping data for this job.

        NOTE: we should scrape all-priority get fields first, then do high
            set priorities, and finally low priority set fields.
        NOTE: this will never raise an exception to prevent killing workers,
            who are building jobs sequentially.

        Returns:
            Optional[Job]: job object constructed from the soup and localization
                of class, returns None if scrape failed.
        """
        # Formulate the get/set actions, we will do these in-sequence
        actions_list = [(True, f) for f in self.job_get_fields]
        actions_list += [(False, f) for f in self.job_set_fields if f in
                         self.high_priority_get_set_fields]
        actions_list += [(False, f) for f in self.job_set_fields if f not in
                         self.high_priority_get_set_fields]

        # Scrape the data for the post, requiring a minimum of info...
        job = None  # type: Union[None, Job]
        job_init_kwargs = self.job_init_kwargs  # NOTE: best to construct once
        for is_get, field in actions_list:

            # Break out immediately because we have failed a filterable
            # condition with something we initialized while scraping.
            # NOTE: if we pre-empt scraping duplicates we cannot update
            # the existing job listing with the new information!
            # TODO: make this configurable?
            if job and self.job_filter.filterable(job):
                if self.job_filter.is_duplicate(job):
                    # FIXME: make this configurable
                    self.logger.debug(
                        f"Scraped job {job.key_id} has key_id "
                        "in known duplicates list. Continuing scrape of job "
                        "to update existing job attributes."
                    )
                else:
                    self.logger.debug(
                        f"Cancelled scraping of {job.key_id}, failed JobFilter"
                    )  # TODO a reason would be nice maybe JobFilterFailure ?
                    break

            # Respectfully delay if it's configured to do so.
            if field in self.delayed_get_set_fields:
                sleep(delay)

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
                    # Crash out gracefully so we can continue scraping.
                    self.logger.warning(
                        f"Unable to scrape {field.name.lower()} for job:"
                        f"\n\t{str(err)}"
                    )
                # Log the job url if we have it.
                # TODO: we should really dump the soup object to an XML file
                # so that users encountering bugs can submit it and we can
                # quickly fix any failing scraping.
                if job.url:
                    self.logger.debug(f"Job URL was {job.url}")

        # Validate job fields if we got something
        if job:
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
        TODO: better way to handle ret type?
        """
        pass

    @abstractmethod
    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField

        NOTE: (remember) do not return anything in here! it sets job attribs
        FIXME: have this automatically set the attribute by JobField.

        Use this to set Job attribs that rely on Job existing already
        with the required minimum fields (i.e. you can set description by
        getting the job's detail page with job.url)
        """
        pass


    def _validate_get_set(self) -> None:
        """Ensure the get/set actions cover all need attribs and dont intersect
        TODO: we should link a helpful article on how to implement get/set mthds
        TODO: we should try to identify if any get/set fields have circ. dep.
        """
        set_job_get_fields = set(self.job_get_fields)
        set_job_set_fields = set(self.job_set_fields)
        all_set_get_fields = set(self.job_get_fields + self.job_set_fields)
        set_min_fields = set(self.min_required_job_fields)

        set_missing_req_fields = set_min_fields - all_set_get_fields
        if set_missing_req_fields:
            raise ValueError(
                f"Scraper: {self.__class__.__name__} Job attributes: "
                f"{set_missing_req_fields} are required and not implemented."
            )

        field_intersection = set_job_get_fields.intersection(set_job_set_fields)
        if field_intersection:
            raise ValueError(
                f"Scraper: {self.__class__.__name__} Job attributes: "
                f"{field_intersection} are implemented by both get() and set()!"
            )
        excluded_fields = []  # type: List[JobField]
        for field in JobField:
            # NOTE: we exclude status, locale, query, provider and scrape date
            # because these are set without needing any scrape data.
            # TODO: SHORT and RAW are not impl. rn. remove this check when impl.
            if (field not in [JobField.STATUS, JobField.LOCALE, JobField.QUERY,
                              JobField.SCRAPE_DATE, JobField.PROVIDER,
                              JobField.SHORT_DESCRIPTION, JobField.RAW]
                    and field not in self.job_get_fields
                    and field not in self.job_set_fields):
                        excluded_fields.append(field)
        if excluded_fields:
            # NOTE: INFO level because this is OK, but ideally ppl see this
            # so they are motivated to help and understand why stuff might
            # be missing in the CSV
            self.logger.info(
                "No get() or set() will be done for Job attrs: "
                f"{[field.name for field in excluded_fields]}"
            )


# Just some basic localized scrapers, you can inherit these to set the locale.
# TODO: move into own file once we get enough of em...
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
