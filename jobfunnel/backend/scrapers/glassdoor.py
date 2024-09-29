"""Scraper for www.glassdoor.X
FIXME: this is currently unable to get past page 1 of job results.
"""

from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor, wait
from math import ceil
import re
from typing import Any, Dict, List, Tuple, Union

from bs4 import BeautifulSoup
from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.scrapers.base import (
    BaseCANEngScraper,
    BaseScraper,
    BaseUKEngScraper,
    BaseUSAEngScraper,
)
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.resources import MAX_CPU_WORKERS, JobField

# pylint: disable=using-constant-test,unused-import
if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.config import JobFunnelConfigManager
# pylint: enable=using-constant-test,unused-import


MAX_GLASSDOOR_LOCATIONS_TO_RETURN = 10
LOCATION_BASE_URL = "https://www.glassdoor.co.in/findPopularLocationAjax.htm?"
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
    def __init__(
        self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter
    ) -> None:
        """Init that contains glassdoor specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_GLASSDOOR_PAGE
        self.query = "-".join(self.config.search_config.keywords)
        # self.driver = get_webdriver() TODO: we can use this if-needed

    @abstractmethod
    def quantize_radius(self, radius: int) -> int:
        """Get the glassdoor-quantized radius"""

    @property
    def job_get_fields(self) -> str:
        """Call self.get(...) for the JobFields in this list when scraping a Job"""
        return [
            JobField.TITLE,
            JobField.COMPANY,
            JobField.LOCATION,
            JobField.POST_DATE,
            JobField.URL,
            JobField.KEY_ID,
            JobField.WAGE,
        ]

    @property
    def job_set_fields(self) -> str:
        """Call self.set(...) for the JobFields in this list when scraping a Job"""
        return [JobField.RAW, JobField.DESCRIPTION]

    @property
    def delayed_get_set_fields(self) -> str:
        """Delay execution when getting /setting any of these attributes of a
        job.

        Override this as needed.
        """
        return [JobField.RAW]

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, sdch, br",
            "accept-language": "en-GB,en-US;q=0.8,en;q=0.6",
            "referer": f"https://www.glassdoor.{self.config.search_config.domain}/",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

    def get_search_url(self, method="get") -> Union[str, Tuple[str, Dict[str, str]]]:
        """Gets the glassdoor search url
        NOTE: we this relies on your city, not the state / province!
        """
        # Form the location lookup request data
        data = {
            "term": self.config.search_config.city,
            "maxLocationsToReturn": MAX_GLASSDOOR_LOCATIONS_TO_RETURN,
        }

        # Get the location id for search location
        location_id = self.session.post(
            LOCATION_BASE_URL, headers=self.headers, data=data
        ).json()[0]["locationId"]

        if method == "get":
            # Form job search url
            search = (
                "https://www.glassdoor.{}/Job/jobs.htm?clickSource=searchBtn"
                "&sc.keyword={}&locT=C&locId={}&jobType=&radius={}".format(
                    self.config.search_config.domain,
                    self.query,
                    location_id,
                    self.quantize_radius(self.config.search_config.radius),
                )
            )
            return search

        elif method == "post":
            # Form the job search url
            search = (
                f"https://www.glassdoor.{self.config.search_config.domain}"
                "/Job/jobs.htm"
            )

            # Form the job search data
            data = {
                "clickSource": "searchBtn",
                "sc.keyword": self.query,
                "locT": "C",
                "locId": location_id,
                "jobType": "",
                "radius": self.quantize_radius(self.config.search_config.radius),
            }

            return search, data
        else:
            raise ValueError(f"No html method {method} exists")

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from a job source into a list of job-soups

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make Job init
        """
        # Get the search url
        search_url, data = self.get_search_url(method="post")

        # Get the search page result.
        request_html = self.session.post(search_url, data=data)
        soup_base = BeautifulSoup(request_html.text, self.config.bs4_parser)

        # Parse total results, and calculate the # of pages needed
        n_pages = self._get_num_search_result_pages(soup_base)
        self.logger.info(
            f"Found {n_pages} pages of search results for query={self.query}"
        )

        # Get the first page of job soups from the search results listings
        job_soup_list = self._parse_job_listings_to_bs4(soup_base)

        # Init threads & futures list FIXME: we should probably delay here too
        threads = ThreadPoolExecutor(MAX_CPU_WORKERS)
        try:
            # Search the remaining pages to extract the list of job soups
            # FIXME: we can't load page 2, it redirects to page 1.
            # There is toast that shows to get email notifs that shows up if
            # I click it myself, must be an event listener?
            futures = []
            if n_pages > 1:
                for page in range(2, n_pages + 1):
                    futures.append(
                        threads.submit(
                            self._search_page_for_job_soups,
                            self._get_next_page_url(soup_base, page),
                            job_soup_list,
                        )
                    )

            wait(futures)  # wait for all scrape jobs to finish
        finally:
            threads.shutdown()

        return job_soup_list

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object by JobField
        TODO: impl div class=compactStars value somewhere.
        """
        if parameter == JobField.TITLE:
            # TODO: we should instead get what user sees in the <span>
            return soup.get("data-normalize-job-title")
        elif parameter == JobField.COMPANY:
            return soup.find(
                "div", attrs={"class", "jobInfoItem jobEmpolyerName"}
            ).text.strip()
        elif parameter == JobField.LOCATION:
            return soup.get("data-job-loc")
        # FIXME: impl.
        # elif parameter == JobField.TAGS:
        #     labels = soup.find_all('div', attrs={'class', 'jobLabel'})
        #     if labels:
        #         return [
        #             l.text.strip() for l in labels if l.text.strip() != 'New'
        #         ]
        #     else:
        #         return []
        # FIXME: impl JobField.REMOTE
        elif parameter == JobField.POST_DATE:
            return calc_post_date_from_relative_str(
                soup.find(
                    "div", attrs={"class": "d-flex align-items-end pl-std css-mi55ob"}
                ).text.strip()
            )
        elif parameter == JobField.WAGE:
            # NOTE: most jobs don't have this so we wont raise a warning here
            # and will fail silently instead
            wage = soup.find("span", attrs={"class": "gray salary"})
            if wage is not None:
                return wage.text.strip()
            else:
                return ""
        elif parameter == JobField.KEY_ID:
            return soup.get("data-id")
        elif parameter == JobField.URL:
            part_url = (
                soup.find("div", attrs={"class", "logoWrap"}).find("a").get("href")
            )
            return (
                f"https://www.glassdoor.{self.config.search_config.domain}"
                f"{part_url}"
            )
        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField
        NOTE: Description has to get and should be respectfully delayed
        """
        if parameter == JobField.RAW:
            job._raw_scrape_data = BeautifulSoup(
                self.session.get(job.url).text, self.config.bs4_parser
            )
        elif parameter == JobField.DESCRIPTION:
            assert job._raw_scrape_data
            job.description = job._raw_scrape_data.find(
                id="JobDescriptionContainer"
            ).text.strip()
        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")

    def _search_page_for_job_soups(
        self, listings_page_url: str, job_soup_list: List[BeautifulSoup]
    ) -> None:
        """Get a list of job soups from a glassdoor page, by loading the page.
        NOTE: this makes GET requests and should be respectfully delayed.
        """
        self.logger.debug(f"Scraping listings page {listings_page_url}")
        job_soup_list.extend(
            self._parse_job_listings_to_bs4(
                BeautifulSoup(
                    self.session.get(listings_page_url).text,
                    self.config.bs4_parser,
                )
            )
        )

    def _parse_job_listings_to_bs4(
        self, page_soup: BeautifulSoup
    ) -> List[BeautifulSoup]:
        """Parse a page of job listings HTML text into job soups"""
        return page_soup.find_all("li", attrs={"class", "jl"})

    def _get_num_search_result_pages(self, soup_base: BeautifulSoup) -> int:
        # scrape total number of results, and calculate the # pages needed
        num_res = soup_base.find("p", attrs={"class", "jobsCount"}).text.strip()
        num_res = int(re.findall(r"(\d+)", num_res.replace(",", ""))[0])
        return int(ceil(num_res / self.max_results_per_page))

    def _get_next_page_url(
        self, soup_base: BeautifulSoup, results_page_number: int
    ) -> str:
        """Construct the next page of search results from the initial search
        results page BeautifulSoup.
        """
        part_url = soup_base.find("li", attrs={"class", "next"}).find("a").get("href")

        assert part_url is not None, "Unable to find next page in listing soup!"

        # Uses partial url to construct next page url
        return re.sub(
            r"_IP\d+\.",
            f"_IP{results_page_number}.",
            f"https://www.glassdoor.{self.config.search_config.domain}" f"{part_url}",
        )


class GlassDoorMetricRadius:
    """Metric units shared by GlassDoorScraperCANEng
    and GlassDoorScraperUKEng
    """

    def quantize_radius(self, radius: int) -> int:
        """convert radius to km FIXME: use numpy.digitize instead"""
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


class GlassDoorScraperCANEng(
    GlassDoorMetricRadius, BaseGlassDoorScraper, BaseCANEngScraper
):
    """Scrapes jobs from www.glassdoor.ca"""


class GlassDoorScraperUSAEng(BaseGlassDoorScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.glassdoor.com"""

    def quantize_radius(self, radius: int) -> int:
        """Get a USA radius (miles)
        FIXME: use numpy.digitize instead
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


class GlassDoorScraperUKEng(
    GlassDoorMetricRadius, BaseGlassDoorScraper, BaseUKEngScraper
):
    """Scrapes jobs from www.glassdoor.co.uk"""
