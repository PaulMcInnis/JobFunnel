"""Base Job class to be populated by Scrapers, manipulated by Filters and saved
to csv / etc by Exporter
"""
from bs4 import BeautifulSoup
from datetime import date, datetime
import re
import string
from typing import Any, Dict, Optional, List

from jobfunnel.resources import (
    Locale, CSV_HEADER, JobStatus, PRINTABLE_STRINGS
)


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
        TODO: perhaps we can do 'remote' for location w/ Enum for those jobs?
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
        self.scrape_date = scrape_date if scrape_date else datetime.now()
        self.tags = tags if tags else []
        if short_description:
            self.short_description = short_description
        else:
            self.short_description = description  # TODO: copy it?

        # Semi-private attrib for debugging
        self._raw_scrape_data = raw

    @property
    def is_remove_status(self) -> bool:
        """Return True if the job's status is one of our removal statuses.
        """
        return self.status in JOB_REMOVE_STATUSES

    @property
    def as_row(self) -> Dict[str, str]:
        """Builds a CSV row dict for this job entry

        TODO: this is legacy, no support for short_description/raw yet.
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

    def clean_strings(self) -> None:
        """Ensure that all string fields have only printable chars
        FIXME: do this automatically upon assignment (override assignment)
        ...This way of doing it is janky and might not work right...
        """
        for attr in [self.title, self.company, self.description, self.tags,
                     self.url, self.key_id, self.provider, self.query,
                     self.wage]:
            attr = ''.join(
                filter(lambda x: x in PRINTABLE_STRINGS, self.title)
            )

    def validate(self) -> None:
        """TODO: implement this just to ensure that the metadata is good"""
        assert self.key_id, "Key_ID is unset!"
