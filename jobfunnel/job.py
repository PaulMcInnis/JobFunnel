"""Base Job class to be populated by Scrapers, manipulated by Filters and saved
to csv / etc by Exporter
"""
from datetime import date
from typing import Any, Optional, List
from jobfunnel.localization import Locale


class Job():
    """The base Job object which contains job information as attribs
    """
    def __init__(self,
                 title: str,
                 company: str,
                 location: str,
                 scrape_date: date,
                 description: str,
                 key_id: str,
                 url: str,
                 locale: Locale,
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
            short_description (str): user-readable short description (one-liner)
            long_description (str): complete description, may be many lines.
            key_id (str): unique identifier for the job TODO: make more robust?
            url (str): link to the page where the job exists
            locale (Locale): identifier to help us with internationalization,
                tells us what language and host-locale/domain a source is in.
            raw (Optional[Any]): raw scrape data that we can use for
                debugging/pickling, defualts to None.
            post_date (Optional[date]): the date the job became available on the
                job source. Defaults to None.
            tags (Optional[List[str]], optional): additional key-words that are
                in the job posting that identify the job. Defaults to [].
        """
        # These must be populated by a Scraper
        self.title = title
        self.company = company
        self.location = location
        self.scrape_date = scrape_date
        self.key_id = key_id
        self.url = url
        self.locale = locale

        # These may not always be populated in our job source
        self.post_date = post_date
        self.tags = tags if tags else []

        # Semi-private attrib for debugging
        self._raw_scrape_data = raw

    def is_valid(self) -> bool:
        """TODO: implement this just to ensure that the metadata is good"""
        pass
