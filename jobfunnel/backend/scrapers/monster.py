"""Scrapers for www.monster.X
"""

from abc import abstractmethod
from math import ceil
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.scrapers.base import (
    BaseCANEngScraper,
    BaseFRFreScraper,
    BaseScraper,
    BaseUKEngScraper,
    BaseUSAEngScraper,
)
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.resources import JobField, Remoteness

# pylint: disable=using-constant-test,unused-import
if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.config import JobFunnelConfigManager
# pylint: enable=using-constant-test,unused-import


MAX_RESULTS_PER_MONSTER_PAGE = 25
MONSTER_SIDEPANEL_TAG_ENTRIES = ["industries", "job type"]  # these --> Job.tags
ID_REGEX = re.compile(
    r"/((?:[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]"
    r"{12})|\d+)"
)


class BaseMonsterScraper(BaseScraper):
    """Scraper for www.monster.X

    NOTE: I dont think it's possible to scrape REMOTE other than from title/desc
        as of sept 2020. -PM
    """

    def __init__(
        self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter
    ) -> None:
        """Init that contains monster specific stuff"""
        super().__init__(session, config, job_filter)
        self.query = "-".join(self.config.search_config.keywords).replace(" ", "-")

        # This is currently not scrapable through Monster site (contents maybe)
        if self.config.search_config.remoteness != Remoteness.ANY:
            self.logger.warning("Monster does not support remoteness in query.")

    @property
    def job_get_fields(self) -> str:
        """Call self.get(...) for the JobFields in this list when scraping a Job"""
        return [
            JobField.KEY_ID,
            JobField.TITLE,
            JobField.COMPANY,
            JobField.LOCATION,
            JobField.POST_DATE,
            JobField.URL,
        ]

    @property
    def job_set_fields(self) -> str:
        """Call self.set(...) for the JobFields in this list when scraping a Job"""
        return [
            JobField.RAW,
            JobField.DESCRIPTION,
            JobField.TAGS,
            JobField.WAGE,
        ]

    @property
    def high_priority_get_set_fields(self) -> List[JobField]:
        """We need to populate these fields first"""
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
        """Session header for monster.X"""
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, sdch, br",
            "accept-language": "en-GB,en-US;q=0.8,en;q=0.6",
            "referer": f"https://www.monster.{self.config.search_config.domain}/",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object by JobField
        NOTE: priority is all the same.
        """
        if parameter == JobField.KEY_ID:
            # TODO: is there a way to combine these calls?
            # NOTE: do not use 'data-m_impr_j_jobid' as this is duplicated
            return (
                soup.find("h2", attrs={"class": "title"})
                .find("a")
                .get("data-m_impr_j_postingid")
            )
        elif parameter == JobField.TITLE:
            return soup.find("h2", attrs={"class": "title"}).text.strip()
        elif parameter == JobField.COMPANY:
            return soup.find("div", attrs={"class": "company"}).text.strip()
        elif parameter == JobField.LOCATION:
            return soup.find("div", attrs={"class": "location"}).text.strip()
        elif parameter == JobField.POST_DATE:
            return calc_post_date_from_relative_str(soup.find("time").text.strip())
        elif parameter == JobField.URL:
            # NOTE: seems that it is a bit hard to view these links? getting 503
            return str(soup.find("a", attrs={"data-bypass": "true"}).get("href"))
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
                "div", attrs={"class": "col-xs-12 cell"}
            )
            if pot_wage_cell:
                pot_wage_value = pot_wage_cell.find("div")
                if pot_wage_value:
                    job.wage = pot_wage_value.text.strip()
        elif parameter == JobField.DESCRIPTION:
            assert job._raw_scrape_data
            job.description = job._raw_scrape_data.find(
                id="JobDescription"
            ).text.strip()
        elif parameter == JobField.TAGS:
            # NOTE: this seems a bit flimsy, monster allows a lot of flex. here
            assert job._raw_scrape_data
            tags = []  # type: List[str]
            for li in job._raw_scrape_data.find_all(
                "section", attrs={"class": "summary-section"}
            ):
                table_key = li.find("dt")
                if (
                    table_key
                    and table_key.text.strip().lower() in MONSTER_SIDEPANEL_TAG_ENTRIES
                ):
                    table_value = li.find("dd")
                    if table_value:
                        tags.append(table_value.text.strip())
        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from a job source into a list of job-soups

        TODO: use threading here too

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make Job init
        """
        # Get the search url
        search_url = self._get_search_url()

        # Load our initial search results listings page
        initial_search_results_html = self.session.get(search_url)
        initial_search_results_soup = BeautifulSoup(
            initial_search_results_html.text, self.config.bs4_parser
        )

        # Parse total results, and calculate the # of pages needed
        n_pages = self._get_num_search_result_pages(initial_search_results_soup)

        # TODO: we should consider expanding the error cases (scrape error page)
        if not n_pages:
            raise ValueError(
                "Unable to identify number of pages of results for query: {}"
                " Please ensure linked page contains results, you may have"
                " provided a city for which there are no results within this"
                " province or state.".format(search_url)
            )

        self.logger.info(
            "Found %d pages of search results for query=%s", n_pages, self.query
        )

        # Get first page of listing soups from our search results listings page
        # NOTE: Monster is an endless-scroll style of job site so we have to
        # Remove previous pages as we go.
        # TODO: better error handling here?
        # TODO: maybe we can move this into get set / BaseScraper somehow?
        def __get_job_soups_by_key_id(
            result_listings: BeautifulSoup,
        ) -> Dict[str, BeautifulSoup]:
            return {
                self.get(JobField.KEY_ID, job_soup): job_soup
                for job_soup in self._get_job_soups_from_search_page(result_listings)
            }

        job_soups_dict = __get_job_soups_by_key_id(initial_search_results_soup)

        # Get all the other pages
        if n_pages > 1:
            for page in range(2, n_pages):
                next_listings_page_soup = BeautifulSoup(
                    self.session.get(self._get_search_url(page=page)).text,
                    self.config.bs4_parser,
                )
                # Add only the jobs that we didn't 'scroll' past already
                job_soups_dict.update(
                    __get_job_soups_by_key_id(next_listings_page_soup)
                )

        # TODO: would be cool if we could avoid key_id scrape duplication in get
        return list(job_soups_dict.values())

    def _get_job_soups_from_search_page(
        self,
        initial_results_soup: BeautifulSoup,
    ) -> List[BeautifulSoup]:
        """Get individual job listing soups from a results page of many jobs"""
        return initial_results_soup.find_all("div", attrs={"class": "flex-row"})

    def _get_num_search_result_pages(
        self,
        initial_results_soup: BeautifulSoup,
    ) -> int:
        """Calculates the number of pages of job listings to be scraped.

        i.e. your search yields 230 results at 50 res/page -> 5 pages of jobs

        Args:
            initial_results_soup: the soup for the first search results page
        Returns:
            The number of pages of job listings to be scraped.
        """
        # scrape total number of results, and calculate the # pages needed
        partial = initial_results_soup.find("h2", "figure").text.strip()
        assert partial, "Unable to identify number of search results"
        num_res = int(re.findall(r"(\d+)", partial)[0])
        return int(ceil(num_res / MAX_RESULTS_PER_MONSTER_PAGE))

    def _get_search_url(self, method: Optional[str] = "get", page: int = 1) -> str:
        """Get the monster search url from SearchTerms
        TODO: implement fulltime/part-time portion + company search?
        TODO: implement POST
        NOTE: unfortunately we cannot start on any page other than 1,
              so the jobs displayed just scrolls forever and we will see
              all previous jobs as we go.
        """
        if method == "get":
            return (
                "https://www.monster.{}/jobs/search/?{}q={}&where={}__2C-{}"
                "&rad={}".format(
                    self.config.search_config.domain,
                    f"page={page}&" if page > 1 else "",
                    self.query,
                    self.config.search_config.city.replace(" ", "-"),
                    self.config.search_config.province_or_state,
                    self._convert_radius(self.config.search_config.radius),
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")

    @abstractmethod
    def _convert_radius(self, radius: int) -> int:
        """NOTE: radius conversion is units/locale specific"""


class MonsterMetricRadius:
    """Metric units shared by MonsterScraperCANEng
    and MonsterScraperUKEng
    """

    def _convert_radius(self, radius: int) -> int:
        """convert radius in miles TODO replace with numpy"""
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


class MonsterScraperCANEng(MonsterMetricRadius, BaseMonsterScraper, BaseCANEngScraper):
    """Scrapes jobs from www.monster.ca"""


class MonsterScraperUSAEng(BaseMonsterScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.monster.com"""

    def _convert_radius(self, radius: int) -> int:
        """convert radius in miles TODO replace with numpy"""
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


class MonsterScraperUKEng(MonsterMetricRadius, BaseMonsterScraper, BaseUKEngScraper):
    """Scrapes jobs from www.monster.co.uk"""

    def _get_search_url(self, method: Optional[str] = "get", page: int = 1) -> str:
        """Get the monster search url from SearchTerms
        TODO: implement fulltime/part-time portion + company search?
        TODO: implement POST
        NOTE: unfortunately we cannot start on any page other than 1,
            so the jobs displayed just scrolls forever and we will see
            all previous jobs as we go.
        """
        if method == "get":
            return (
                "https://www.monster.{}/jobs/search/?{}q={}&where={}"
                "&rad={}".format(
                    self.config.search_config.domain,
                    f"page={page}&" if page > 1 else "",
                    self.query,
                    self.config.search_config.city.replace(" ", "-"),
                    self._convert_radius(self.config.search_config.radius),
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")


class MonsterScraperFRFre(MonsterMetricRadius, BaseMonsterScraper, BaseFRFreScraper):
    """Scrapes jobs from www.monster.fr"""

    def _get_search_url(self, method: Optional[str] = "get", page: int = 1) -> str:
        """Get the monster search url from SearchTerms
        TODO: implement fulltime/part-time portion + company search?
        TODO: implement POST
        NOTE: unfortunately we cannot start on any page other than 1,
              so the jobs displayed just scrolls forever and we will see
              all previous jobs as we go.
        """
        if method == "get":
            return (
                "https://www.monster.{}/emploi/recherche/?{}q={}&where={}__2C-{}"
                "&rad={}".format(
                    self.config.search_config.domain,
                    f"page={page}&" if page > 1 else "",
                    self.query,
                    self.config.search_config.city.replace(" ", "-"),
                    self.config.search_config.province_or_state,
                    self._convert_radius(self.config.search_config.radius),
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")
