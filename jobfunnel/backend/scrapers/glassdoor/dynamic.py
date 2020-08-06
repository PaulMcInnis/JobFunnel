"""Base class for scraping jobs from GlassDoor
"""
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, wait
import logging
from requests import post, Session
from typing import Dict, List, Tuple, Optional

from jobfunnel.backend import Job
from jobfunnel.backend.tools import get_webdriver
from jobfunnel.backend.localization import Locale
from jobfunnel.backend.scrapers.glassdoor.base import GlassDoorBase


class GlassDoorDynamic(GlassDoorBase):
    """The Dynamic Version of the GlassDoor scraper, that uses selenium to scrape job postings.
    """

    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger):
        """Init"""
        super().__init__(session, config, logger)
        self.driver = get_webdriver()

    def scrape(self):
        # FIXME: impl!
        pass


class GlassDoorDynamicCAEng(GlassDoorDynamic):

    @property
    def locale(self) -> Locale:
        """Get the localizations that this scraper was built for
        We will use this to put the right filters & scrapers together
        """
        return Locale.CANADA_ENGLISH

