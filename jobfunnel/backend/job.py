"""Base Job class to be populated by Scrapers, manipulated by Filters and saved
to csv / etc by Exporter
"""
from copy import deepcopy
from datetime import date, datetime
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from jobfunnel.resources import (CSV_HEADER, MAX_BLOCK_LIST_DESC_CHARS,
                                 MIN_DESCRIPTION_CHARS, PRINTABLE_STRINGS,
                                 JobStatus, Locale)

# If job.status == one of these we filter it out of results
JOB_REMOVE_STATUSES = [
    JobStatus.DELETE, JobStatus.ARCHIVE, JobStatus.REJECTED, JobStatus.OLD
]


class Job():
    """The base Job object which contains job information as attribs
    """
    def __init__(self,
                 title: str,
                 company: str,
                 location: str,
                 description: str,
                 url: str,
                 locale: Locale,
                 query: str,
                 provider: str,
                 status: JobStatus,
                 key_id: Optional[str] = '',
                 scrape_date: Optional[date] = None,
                 short_description: Optional[str] = None,
                 post_date: Optional[date] = None,
                 raw: Optional[BeautifulSoup] = None,
                 wage: Optional[str] = None,
                 tags: Optional[List[str]] = None,
                 remote: Optional[str] = None) -> None:
        """Object to represent a single job that we have scraped

        TODO integrate init with JobField somehow, ideally with validation.
        TODO: would be nice to use something standardized for location str
        TODO: wage ought to be a number or an object, but is str for flexibility
        NOTE: ideally key_id is provided, but Monster sets() it, so it now
            has a default = None and is checked for in validate()

        Args:
            title (str): title of the job (should be somewhat short)
            company (str): company the job was posted for (should also be short)
            location (str): string that tells the user where the job is located
            description (str): content of job description, ideally this is human
                readable.
            key_id (str): unique identifier for the job TODO: make more robust?
            url (str): link to the page where the job exists
            locale (Locale): identifier to help us with internationalization,
                tells us what the locale of the scraper was that scraped this
                job.
            query (str): the search string that this job was found with
            provider (str): name of the job source
            status (JobStatus): the status of the job (i.e. new)
            scrape_date (Optional[date]): date the job was scraped, Defaults
                to the time that the job object is created.
            short_description (Optional[str]): user-readable short description
                (one-liner)
            post_date (Optional[date]): the date the job became available on the
                job source. Defaults to None.
            raw (Optional[BeautifulSoup]): raw scrape data that we can use for
                debugging/pickling, defualts to None.
            wage (Optional[str], optional): string describing wage (may be est)
            tags (Optional[List[str]], optional): additional key-words that are
                in the job posting that identify the job. Defaults to [].
            remote (Optional[str], optional): string describing remote work
                allowance/status i.e. ('temporarily remote', 'fully remote' etc)
        """
        # These must be populated by a Scraper
        self.title = title
        self.company = company
        self.location = location
        self.description = description
        self.key_id = key_id
        self.url = url
        self.locale = locale
        self.query = query
        self.provider = provider
        self.status = status
        self.wage = wage
        self.remote = remote

        # These may not always be populated in our job source
        self.post_date = post_date
        self.scrape_date = scrape_date if scrape_date else datetime.today()
        self.tags = tags if tags else []
        if short_description:
            self.short_description = short_description
        else:
            self.short_description = ''

        # Semi-private attrib for debugging
        self._raw_scrape_data = raw

    @property
    def is_remove_status(self) -> bool:
        """Return True if the job's status is one of our removal statuses.
        """
        return self.status in JOB_REMOVE_STATUSES

    def update_if_newer(self, job: 'Job') -> bool:
        """Update an existing job with new metadata but keep user's status,
        but only if the job.post_date > existing_job.post_date!

        NOTE: if you have hours or minutes or seconds set, and jobs were scraped
        on the same day, the comparison will favour the extra info as newer!
        TODO: we should do more checks to ensure we are not seeing a totally
        different job by accident (since this check is usually done by key_id)
        TODO: more elegant way? maybe we can deepcopy self?
        TODO: Currently we do day precision but if we wanted to update because
        something is newer by hours we will need to revisit this limitation and
        store scrape hour/etc in the CSV as well.

        Returns:
            True if we updated self with job, False if we didn't
        """
        if (job.post_date > self.post_date):
            # Update all attrs other than status (which user can set).
            self.company = deepcopy(job.company)
            self.location = deepcopy(job.location)
            self.description = deepcopy(job.description)
            self.key_id = deepcopy(job.key_id) # NOTE: be careful doing this!
            self.url = deepcopy(job.url)
            self.locale = deepcopy(job.locale)
            self.query = deepcopy(job.query)
            self.provider = deepcopy(job.provider)
            self.status = deepcopy(job.status)
            self.wage = deepcopy(job.wage)
            self.remote = deepcopy(job.remote)
            self.post_date = deepcopy(job.post_date)
            self.scrape_date = deepcopy(job.scrape_date)
            self.tags = deepcopy(job.tags)
            self.short_description = deepcopy(job.short_description)
            self._raw_scrape_data = deepcopy(job._raw_scrape_data)
            return True
        else:
            return False

    def is_old(self, max_age: datetime) -> bool:
        """Identify if a job is older than a certain max_age

        Args:
            max_age_days: maximum allowable age for a job

        Returns:
            True if it's older than number of days
            False if it's fresh enough to keep
        """
        return self.post_date < max_age

    @property
    def as_row(self) -> Dict[str, str]:
        """Builds a CSV row dict for this job entry

        TODO: this is legacy, no support for short_description yet.
        NOTE: RAW cannot be put into CSV.
        """
        return dict([
            (h, v) for h,v in zip(
                CSV_HEADER,
                [
                    self.status.name,
                    self.title,
                    self.company,
                    self.location,
                    self.post_date.strftime('%Y-%m-%d'),
                    self.description,
                    ', '.join(self.tags),
                    self.url,
                    self.key_id,
                    self.provider,
                    self.query,
                    self.locale.name,
                    self.wage,
                    self.remote,
                ]
            )
        ])

    @property
    def as_json_entry(self) -> Dict[str, str]:
        """This formats a job for the purpose of saving it to a block JSON
        i.e. duplicates list file or user's block list file
        NOTE: we truncate descriptions in block lists, TODO: use 'short' desc
        """
        return {
            'title': self.title,
            'company': self.company,
            'post_date': self.post_date.strftime('%Y-%m-%d'),
            'description': (
                    self.description[:MAX_BLOCK_LIST_DESC_CHARS]
                    + '..'
                )
                if len(self.description) > MAX_BLOCK_LIST_DESC_CHARS
                else self.description,
            'status': self.status.name,
        }

    def clean_strings(self) -> None:
        """Ensure that all string fields have only printable chars
        TODO: do this automatically upon assignment (override assignment)
        TODO: maybe we can use stopwords?
        """
        for attr in [self.title, self.company, self.description, self.tags,
                     self.url, self.key_id, self.provider, self.query,
                     self.wage]:
            attr = ''.join(
                filter(lambda x: x in PRINTABLE_STRINGS, self.title)
            )

    def validate(self) -> None:
        """Simple checks just to ensure that the metadata is good
        TODO: consider expanding to cover all attribs.
        """
        assert self.key_id, "Key_ID is unset!"
        assert self.title, "Title is unset!"
        assert self.company, "Company is unset!"
        assert self.url, "URL is unset!"
        if len(self.description) < MIN_DESCRIPTION_CHARS:
            raise ValueError("Description too short!")
