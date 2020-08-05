"""Base class for scraping jobs from GlassDoor
"""
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, wait
import logging
from requests import post, Session
from typing import Dict, List, Tuple, Optional

from jobfunnel.backend import Job
from jobfunnel.backend.tools import get_webdriver
from jobfunnel.backend.localization import Locale, get_domain_from_locale
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

    @property
    def headers(self) -> Dict[str, str]:
        return{
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                get_domain_from_locale(self.locale)
            ),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }

