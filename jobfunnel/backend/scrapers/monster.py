"""Scrapers for www.monster.X
"""
import re
from abc import abstractmethod
from math import ceil
from typing import Any, Dict, List, Tuple

from bs4 import BeautifulSoup
from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.scrapers.base import (BaseCANEngScraper, BaseScraper,
                                             BaseUSAEngScraper, BaseUKEngScraper,
                                             BaseFRFreScraper)
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.resources import JobField, Remoteness

# pylint: disable=using-constant-test,unused-import
if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.config import JobFunnelConfigManager
# pylint: enable=using-constant-test,unused-import


MAX_RESULTS_PER_MONSTER_PAGE = 25
MONSTER_SIDEPANEL_TAG_ENTRIES = ['industries', 'job type']  # these --> Job.tags
ID_REGEX = re.compile(
    r'/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]'
    r'{12})|\d+)'
)


class BaseMonsterScraper(BaseScraper):
    """Scraper for www.monster.X

    NOTE: I dont think it's possible to scrape REMOTE other than from title/desc
        as of sept 2020. -PM
    """

    def __init__(self, session: Session, config: 'JobFunnelConfigManager',
                 job_filter: JobFilter) -> None:
        """Init that contains monster specific stuff
        """
        super().__init__(session, config, job_filter)
        self.query = '-'.join(
            self.config.search_config.keywords
        ).replace(' ', '-')

        # This is currently not scrapable through Monster site (contents maybe)
        if self.config.search_config.remoteness != Remoteness.ANY:
            self.logger.warning("Monster does not support remoteness in query.")

    @property
    def job_get_fields(self) -> str:
        """Call self.get(...) for the JobFields in this list when scraping a Job
        """
        return [
            JobField.KEY_ID, JobField.TITLE, JobField.COMPANY,
            JobField.LOCATION, JobField.POST_DATE, JobField.URL,
        ]

    @property
    def job_set_fields(self) -> str:
        """Call self.set(...) for the JobFields in this list when scraping a Job
        """
        return [
            JobField.RAW, JobField.DESCRIPTION, JobField.TAGS, JobField.WAGE,
        ]

    @property
    def high_priority_get_set_fields(self) -> List[JobField]:
        """We need to populate these fields first
        """
        return [JobField.RAW, JobField.KEY_ID]

    @property
    def delayed_get_set_fields(self) -> str:
        """Delay execution when getting /setting any of these attributes of a
        job.

        Override this as needed.
        """
        return [JobField.RAW]

    @property
    def headers(self) -> Dict[str, str]:
        """Session header for monster.X
        """
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
                      'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer':
                f'https://www.monster.{self.config.search_config.domain}/',
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

    def _extract_pages_and_total_listings(self, soup: BeautifulSoup) -> Tuple[int, int]:
        """Method to extract the total number of listings and pages."""
        # scrape total number of results, and calculate the # pages needed
        partial = soup.find('h2', 'figure').text.strip()
        assert partial, "Unable to identify number of search results"
        num_res = int(re.findall(r'(\d+)', partial)[0])
        n_pages = int(ceil(num_res / MAX_RESULTS_PER_MONSTER_PAGE))

        return (num_res, n_pages)

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object by JobField
        NOTE: priority is all the same.
        """
        if parameter == JobField.KEY_ID:
            # TODO: is there a way to combine these calls?
            # NOTE: do not use 'data-m_impr_j_jobid' as this is duplicated
            return soup.find('h2', attrs={'class': 'title'}).find('a').get(
                'data-m_impr_j_postingid'
            )
        elif parameter == JobField.TITLE:
            return soup.find('h2', attrs={'class': 'title'}).text.strip()
        elif parameter == JobField.COMPANY:
            return soup.find('div', attrs={'class': 'company'}).text.strip()
        elif parameter == JobField.LOCATION:
            return soup.find('div', attrs={'class': 'location'}).text.strip()
        elif parameter == JobField.POST_DATE:
            return calc_post_date_from_relative_str(
                soup.find('time').text.strip()
            )
        elif parameter == JobField.URL:
            # NOTE: seems that it is a bit hard to view these links? getting 503
            return str(
                soup.find('a', attrs={'data-bypass': 'true'}).get('href')
            )
        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField
        NOTE: priority is: HIGH: RAW, LOW: DESCRIPTION / TAGS
        """
        if parameter == JobField.RAW:
            job._raw_scrape_data = BeautifulSoup(
                self.session.get(job.url).text, self.config.bs4_parser
            )
        elif parameter == JobField.WAGE:
            pot_wage_cell = job._raw_scrape_data.find(
                'div', attrs={'class': 'col-xs-12 cell'}
            )
            if pot_wage_cell:
                pot_wage_value = pot_wage_cell.find('div')
                if pot_wage_value:
                    job.wage = pot_wage_value.text.strip()
        elif parameter == JobField.DESCRIPTION:
            assert job._raw_scrape_data
            job.description = job._raw_scrape_data.find(
                id='JobDescription'
            ).text.strip()
        elif parameter == JobField.TAGS:
            # NOTE: this seems a bit flimsy, monster allows a lot of flex. here
            assert job._raw_scrape_data
            tags = []  # type: List[str]
            for li in job._raw_scrape_data.find_all(
                    'section', attrs={'class': 'summary-section'}):
                table_key = li.find('dt')
                if (table_key and table_key.text.strip().lower()
                        in MONSTER_SIDEPANEL_TAG_ENTRIES):
                    table_value = li.find('dd')
                    if table_value:
                        tags.append(table_value.text.strip())
        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")

    def _parse_job_listings_to_bs4(self, page_soup: BeautifulSoup
                                   ) -> List[BeautifulSoup]:
        """Parse a page of job listings HTML text into job soups
        """
        return page_soup.find_all('div', attrs={'class': 'flex-row'})

    def _get_search_stem_url(self) -> str:
        """Get the search stem url for initial search."""
        return f"https://www.monster.{self.config.search_config.domain}/jobs/search/"

    def _get_search_args(self) -> Dict[str, str]:
        """Get all arguments used for the search query."""
        return {
            'q': self.query,
            'where': f"{self.config.search_config.city}__2C-{self.config.search_config.province_or_state}",
            'rad': self._convert_radius(self.config.search_config.radius),
        }

    def _get_page_query(self, page: int) -> Tuple[str, str]:
        """Return query parameter and value for specific provider."""
        return ('page', page)

    @abstractmethod
    def _convert_radius(self, radius: int) -> int:
        """NOTE: radius conversion is units/locale specific
        """


class MonsterMetricRadius:
    """Metric units shared by MonsterScraperCANEng
        and MonsterScraperUKEng
    """

    def _convert_radius(self, radius: int) -> int:
        """ convert radius in miles TODO replace with numpy
        """
        if radius < 5:
            radius = 0
        elif 5 <= radius < 10:
            radius = 5
        elif 10 <= radius < 20:
            radius = 10
        elif 20 <= radius < 50:
            radius = 20
        elif 50 <= radius < 100:
            radius = 50
        elif radius >= 100:
            radius = 100
        return radius


class MonsterScraperCANEng(MonsterMetricRadius, BaseMonsterScraper,
                           BaseCANEngScraper):
    """Scrapes jobs from www.monster.ca
    """


class MonsterScraperUSAEng(BaseMonsterScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.monster.com
    """

    def _convert_radius(self, radius: int) -> int:
        """convert radius in miles TODO replace with numpy
        """
        if radius < 5:
            radius = 0
        elif 5 <= radius < 10:
            radius = 5
        elif 10 <= radius < 20:
            radius = 10
        elif 20 <= radius < 30:
            radius = 20
        elif 30 <= radius < 40:
            radius = 30
        elif 40 <= radius < 50:
            radius = 40
        elif 50 <= radius < 60:
            radius = 50
        elif 60 <= radius < 75:
            radius = 60
        elif 75 <= radius < 100:
            radius = 75
        elif 100 <= radius < 150:
            radius = 100
        elif 150 <= radius < 200:
            radius = 150
        elif radius >= 200:
            radius = 200
        return radius


class MonsterScraperUKEng(MonsterMetricRadius, BaseMonsterScraper,
                          BaseUKEngScraper):
    """Scrapes jobs from www.monster.co.uk
    """
    def _get_search_args(self) -> Dict[str, str]:
        """Get all arguments used for the search query."""
        # first get arguments from parent class, then override the location
        args = super()._get_search_args()
        args['where'] = self.config.search_config.city

        return args

class MonsterScraperFRFre(MonsterMetricRadius, BaseMonsterScraper,
                           BaseFRFreScraper):
    """Scrapes jobs from www.monster.fr
    """
    def _get_search_stem_url(self) -> str:
        """Get the search stem url for initial search."""
        return f"https://www.monster.{self.config.search_config.domain}/emploi/recherche/"
