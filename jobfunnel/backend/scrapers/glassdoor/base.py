"""Base Glassdoor Scraper used by both the selenium and statis scrapers
"""
import logging
from requests import Session
from typing import Dict, List, Tuple, Optional, Union

from jobfunnel.backend.scrapers import BaseScraper


MAX_LOCATIONS_TO_RETURN = 10
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

class GlassDoorBase(BaseScraper):

    def __init__(self, session: Session, config: 'JobFunnelConfig',
                 logger: logging.Logger):
        """Init that contains glassdoor specific stuff
        """
        super().__init__(session, config, logger)
        self.max_results_per_page = MAX_RESULTS_PER_GLASSDOOR_PAGE
        self.query_string = '-'.join(self.config.search_terms.keywords)

    @property
    def headers(self) -> Dict[str, str]:
        return{
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': f'https://www.glassdoor.{self.domain}/',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }

    def get_search_url(self,
                       method='get') -> Union[str, Tuple[str, Dict[str,str]]]:
        """Gets the glassdoor search url
        NOTE: we this relies on your city, not the state / province!
        """
        # Form the location lookup request data
        data = {
            'term': self.config.search_terms.city,
            'maxLocationsToReturn': MAX_LOCATIONS_TO_RETURN
        }

        # Get the location id for search location
        location_response = self.session.post(
            LOCATION_BASE_URL, headers=self.headers, data=data
        ).json()

        if method == 'get':

            # Form job search url
            search = (
                'https://www.glassdoor.{}/Job/jobs.htm?clickSource=searchBtn'
                '&sc.keyword={}&locT=C&locId={}&jobType=&radius={}'.format(
                    self.domain,
                    self.query_string,
                    location_response[0]['locationId'],
                    self.quantize_radius(self.config.search_terms.radius),
                )
            )
            return search

        elif method == 'post':

            # Form the job search url
            search = "https://www.glassdoor.{}/Job/jobs.htm".format(
                self.domain
            )

            # Form the job search data
            data = {
                'clickSource': 'searchBtn',
                'sc.keyword': self.query_string,
                'locT': 'C',
                'locId': location_response[0]['locationId'],
                'jobType': '',
                'radius': self.quantize_radius(
                    self.config.search_terms.radius
                ),
            }

            return search, data
        else:

            raise ValueError(f'No html method {method} exists')


    def quantize_radius(self, radius: int) -> int:
        """function that quantizes the user input radius to a valid radius
           value: 10, 20, 30, 50, 100, and 200 kilometers
        FIXME: use numpy.digitize instead
        """
        if self.locale == Locale.USA_ENGLISH:
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
            return radius
        else:
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
