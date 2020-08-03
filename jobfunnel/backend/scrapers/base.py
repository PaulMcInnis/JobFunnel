"""The base scraper class to be used for all web-scraping emitting Job objects
"""
from abc import ABC, abstractmethod
import logging
import os
from typing import Dict, List
import random
from requests import Session

from jobfunnel import USER_AGENT_LIST
from jobfunnel.backend import Job
from jobfunnel.backend.localization import Locale
#from jobfunnel.config import JobFunnelConfig  FIXME: circular imports issue


class BaseScraper(ABC):
    """Base scraper object, for generating List[Job] from a specific job source

    TODO: accept filters: List[Filter] here if we have Filter(ABC)
    NOTE: we want to use filtering here because scraping blurbs can be slow.
    """

    @abstractmethod
    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger) -> None:
        # TODO: can we set self.session etc so inherited classes don't have to?
        pass

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

    @abstractmethod
    def scrape(self) -> Dict[str, Job]:
        """Scrapes raw data from a job source into a list of Job objects

        Returns:
            List[Job]: list of jobs scraped from the job source
        """
        pass
