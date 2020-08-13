"""Base class for scraping jobs from GlassDoor
"""
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date, datetime, timedelta
import logging
from math import ceil
from time import sleep, time
from typing import Dict, List, Tuple, Optional, Any
import re
from requests import Session

from bs4 import BeautifulSoup

from jobfunnel.resources import Locale, MAX_CPU_WORKERS, JobField
from jobfunnel.backend import Job, JobStatus
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.backend.scrapers.base import (
    BaseCANEngScraper, BaseUSAEngScraper
)
from jobfunnel.backend.scrapers.glassdoor.base import BaseGlassDoorScraper


# FIXME: maybe we can just move this to a dev branch?
class DrivenGlassDoorScraper(BaseGlassDoorScraper):
    """The Dynamic Version of the GlassDoor scraper, that uses selenium to scrape job postings.
    """

    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger):
        """Init"""
        super().__init__(session, config, logger)
        #self.driver = get_webdriver()


    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        pass
        # search_url, data = self.get_search_url()
        # self.driver.get(search_url)


class DrivenGlassDoorScraperCANEng(DrivenGlassDoorScraper, BaseCANEngScraper):
    pass

class DrivenGlassDoorScraperUSAEng(DrivenGlassDoorScraper, BaseUSAEngScraper):
    pass