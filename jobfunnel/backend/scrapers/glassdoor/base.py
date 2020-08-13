"""Base Glassdoor Scraper used by both the selenium (driven) and static scrapers
"""
from abc import abstractmethod
from bs4 import BeautifulSoup
import logging
from requests import Session
from typing import Dict, List, Tuple, Optional, Union

from jobfunnel.backend.scrapers.base import (
    BaseScraper, BaseCANEngScraper, BaseUSAEngScraper
)


MAX_GLASSDOOR_LOCATIONS_TO_RETURN = 10
LOCATION_BASE_URL = 'https://www.glassdoor.co.in/findPopularLocationAjax.htm?'
MAX_RESULTS_PER_GLASSDOOR_PAGE = 30
GLASSDOOR_RADIUS_MAP = {
    0: 0,
    10: 6,
    20: 12,
    30: 19,
    50: 31,
    100: 62,
    200: 124,
}

class BaseGlassDoorScraper(BaseScraper):

    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger):
        """Init that contains glassdoor specific stuff
        """
        super().__init__(session, config, logger)
        self.max_results_per_page = MAX_RESULTS_PER_GLASSDOOR_PAGE
        self.query = '-'.join(self.config.search_config.keywords)

    @property
    def headers(self) -> Dict[str, str]:
        return{
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer':
                f'https://www.glassdoor.{self.config.search_config.domain}/',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }


    @abstractmethod
    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from a job source into a list of job-soups

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make Job init
        """
        pass


    def get_search_url(self,
                       method='get') -> Union[str, Tuple[str, Dict[str,str]]]:
        """Gets the glassdoor search url
        NOTE: we this relies on your city, not the state / province!
        """
        # Form the location lookup request data
        data = {
            'term': self.config.search_config.city,
            'maxLocationsToReturn': MAX_GLASSDOOR_LOCATIONS_TO_RETURN,
        }

        # Get the location id for search location
        location_id = self.session.post(
            LOCATION_BASE_URL, headers=self.headers, data=data
        ).json()[0]['locationId']

        if method == 'get':

            # Form job search url
            search = (
                'https://www.glassdoor.{}/Job/jobs.htm?clickSource=searchBtn'
                '&sc.keyword={}&locT=C&locId={}&jobType=&radius={}'.format(
                    self.config.search_config.domain,
                    self.query,
                    location_id,
                    self.quantize_radius(self.config.search_config.radius),
                )
            )
            return search

        elif method == 'post':

            # Form the job search url
            search = (
                f"https://www.glassdoor.{self.config.search_config.domain}"
                "/Job/jobs.htm"
            )

            # Form the job search data
            data = {
                'clickSource': 'searchBtn',
                'sc.keyword': self.query,
                'locT': 'C',
                'locId': location_id,
                'jobType': '',
                'radius':
                    self.quantize_radius(self.config.search_config.radius),
            }

            return search, data
        else:

            raise ValueError(f'No html method {method} exists')

    @abstractmethod
    def quantize_radius(self, radius: int) -> int:
        """Get the glassdoor-quantized radius
        FIXME: use numpy.digitize instead
        """
        pass


class BaseGlassDoorScraperCANEng(BaseGlassDoorScraper, BaseCANEngScraper):

    def quantize_radius(self, radius: int) -> int:
        """Get a Canadian raduius (km)
        """
        if radius < 10:
            radius = 0
        elif 10 <= radius < 20:
            radius = 10
        elif 20 <= radius < 30:
            radius = 20
        elif 30 <= radius < 50:
            radius = 30
        elif 50 <= radius < 100:
            radius = 50
        elif 100 <= radius < 200:
            radius = 100
        elif radius >= 200:
            radius = 200
        return GLASSDOOR_RADIUS_MAP[radius]


class BaseGlassDoorScraperUSAEng(BaseGlassDoorScraper, BaseUSAEngScraper):

    def quantize_radius(self, radius: int) -> int:
        """Get a USA raduius (miles)
        """
        if radius < 5:
            radius = 0
        elif 5 <= radius < 10:
            radius = 5
        elif 10 <= radius < 15:
            radius = 10
        elif 15 <= radius < 25:
            radius = 15
        elif 25 <= radius < 50:
            radius = 25
        elif 50 <= radius < 100:
            radius = 50
        elif radius >= 100:
            radius = 100
        return GLASSDOOR_RADIUS_MAP[radius]
