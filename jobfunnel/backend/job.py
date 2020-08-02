"""Base Job class to be populated by Scrapers, manipulated by Filters and saved
to csv / etc by Exporter
"""
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from enum import Enum
import re
import string
from typing import Any, Dict, Optional, List

from jobfunnel.backend.localization import Locale
from jobfunnel.resources.resources import CSV_HEADER


PRINTABLE_STRINGS = set(string.printable)

# Initialize list and store regex objects of date quantifiers TODO: refactor
HOUR_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?(?:hour|hr)')
DAY_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?(?:day|d)')
MONTH_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?month')
YEAR_REGEX = re.compile(r'(\d+)(?:[ +]{1,3})?year')
RECENT_REGEX_A = re.compile(r'[tT]oday|[jJ]ust [pP]osted')
RECENT_REGEX_B = re.compile(r'[yY]esterday')


class JobStatus(Enum):
    """Job statuses that are built-into jobfunnel
    """
    NEW = 1
    ARCHIVE = 2
    INTERVIEWING = 3
    INTERVIEWED = 4
    REJECTED = 5
    ACCEPTED = 6


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

    def get_csv_row(self) -> Dict[str, str]:
        """Builds a CSV row for this job entry

        TODO: this is legacy, no support for short_description/raw rn.
        """
        return dict([
            (h, v) for h,v in zip(
                CSV_HEADER,
                [
                    self.status.name,
                    self.title,
                    self.company,
                    self.location,
                    self.post_date,
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
        TODO: do this automatically upon assignment (override assignment)
        """
        for attr in vars(self):
            if type(attr) == str:
                self.attr = ''.join(
                    filter(lambda x: x in PRINTABLE_STRINGS, self.title)
                )

    def set_post_date_from_relative_date(self) -> None:
        """Identifies a job's post date via post age, updates in-place
        """
        post_date = None
        # Supports almost all formats like 7 hours|days and 7 hr|d|+d
        try:
            # hours old
            hours_ago = HOUR_REGEX.findall(self.post_date)[0]
            post_date = datetime.now() - timedelta(hours=int(hours_ago))
        except IndexError:
            # days old
            try:
                days_ago = DAY_REGEX.findall(self.post_date)[0]
                post_date = datetime.now() - timedelta(days=int(days_ago))
            except IndexError:
                # months old
                try:
                    months_ago = MONTH_REGEX.findall(self.post_date)[0]
                    post_date = datetime.now() - relativedelta(
                        months=int(months_ago))
                except IndexError:
                    # years old
                    try:
                        years_ago = YEAR_REGEX.findall(self.post_date)[0]
                        post_date = datetime.now() - relativedelta(
                            years=int(years_ago))
                    except IndexError:
                        # try phrases like today, just posted, or yesterday
                        if (RECENT_REGEX_A.findall(self.post_date) and
                                not post_date):
                            # today
                            post_date = datetime.now()
                        elif RECENT_REGEX_B.findall(self.post_date):
                            # yesterday
                            post_date = datetime.now() - timedelta(days=int(1))
                        elif not post_date:
                            # we have failed.
                            raise ValueError(
                                f"Unable to calculate date for {self.title}"
                            )

        # Format date in standard format e.g. 2020-01-01
        self.post_date = post_date.strftime('%Y-%m-%d')

    def validate(self) -> None:
        """TODO: implement this just to ensure that the metadata is good"""
        pass
