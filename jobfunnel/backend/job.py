"""Base Job class to be populated by Scrapers, manipulated by Filters and saved
to csv / etc by Exporter
"""
from datetime import date, datetime
from enum import Enum
import re
import string
from typing import Any, Dict, Optional, List

from jobfunnel.backend.localization import Locale
from jobfunnel.resources.resources import CSV_HEADER


PRINTABLE_STRINGS = set(string.printable)

class JobStatus(Enum):
    """Job statuses that are built-into jobfunnel
    """
    UNKNOWN = 1
    NEW = 2
    ARCHIVE = 3
    INTERVIEWING = 4
    INTERVIEWED = 5
    REJECTED = 6
    ACCEPTED = 7
    DELETE = 8
    INTERESTED = 9
    APPLIED = 10
    APPLY = 11


REMOVE_STATUSES = [JobStatus.DELETE, JobStatus.ARCHIVE, JobStatus.REJECTED]


class Job():
    """The base Job object which contains job information as attribs
    """
    def __init__(self,
                 title: str,
                 company: str,
                 location: str,
                 description: str,
                 key_id: str,
                 url: str,
                 locale: Locale,
                 query: str,
                 provider: str,
                 status: JobStatus,
                 scrape_date: Optional[date] = None,
                 short_description: Optional[str] = None,
                 post_date: Optional[date] = None,
                 raw: Optional[Any] = None,
                 tags: Optional[List[str]] = None) -> None:
        """[summary]

        TODO: would be nice to use something standardized for location
        TODO: perhaps we can do 'remote' for location w/ Enum for those jobs?

        Args:
            title (str): title of the job (should be somewhat short)
            company (str): company the job was posted for (should also be short)
            location (str): string that tells the user where the job is located
            description (str): content of job description, ideally this is human
                readable.
            key_id (str): unique identifier for the job TODO: make more robust?
            url (str): link to the page where the job exists
            locale (Locale): identifier to help us with internationalization,
                tells us what language and host-locale/domain a source is in.
            query (str): the search string that this job was found with
            provider (str): name of the job source
            status (JobStatus): the status of the job (i.e. new)
            scrape_date (Optional[date]): date the job was scraped, Defaults
                to the time that the job object is created.
            short_description (Optional[str]): user-readable short description
                (one-liner)
            post_date (Optional[date]): the date the job became available on the
                job source. Defaults to None.
            raw (Optional[Any]): raw scrape data that we can use for
                debugging/pickling, defualts to None.
            tags (Optional[List[str]], optional): additional key-words that are
                in the job posting that identify the job. Defaults to [].
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
        return self.status in REMOVE_STATUSES

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
                ]
            )
        ])

    def clean_strings(self) -> None:
        """Ensure that all string fields have only printable chars
        FIXME: do this automatically upon assignment (override assignment)
        ...This way of doing it is janky and might not work right...
        """
        for attr in [self.title, self.company, self.description, self.tags,
                     self.url, self.key_id, self.provider, self.query]:
            attr = ''.join(
                filter(lambda x: x in PRINTABLE_STRINGS, self.title)
            )

    def validate(self) -> None:
        """TODO: implement this just to ensure that the metadata is good"""
        pass
