"""Scraper designed to get jobs from www.indeed.X
"""

from concurrent.futures import ThreadPoolExecutor, wait
import json
from math import ceil
import random
import re
from typing import Any, Dict, List, Optional
from unicodedata import normalize

from bs4 import BeautifulSoup
from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.scrapers.base import (
    BaseCANEngScraper,
    BaseDEGerScraper,
    BaseFRFreScraper,
    BaseScraper,
    BaseUKEngScraper,
    BaseUSAEngScraper,
)
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.resources import (
    MAX_CPU_WORKERS,
    USER_AGENT_LIST_MOBILE,
    JobField,
    Remoteness,
)

# pylint: disable=using-constant-test,unused-import
if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.config import JobFunnelConfigManager
# pylint: enable=using-constant-test,unused-import

ID_REGEX = re.compile(r"id=\"sj_([a-zA-Z0-9]*)\"")
MAX_RESULTS_PER_INDEED_PAGE = 20  # 20 results for mobile, 50 for desktop
# NOTE: these magic strings stick for both the US and CAN indeed websites...
FULLY_REMOTE_MAGIC_STRING = "&remotejob=032b3046-06a3-4876-8dfd-474eb5e7ed11"
COVID_REMOTE_MAGIC_STRING = "&remotejob=7e3167e4-ccb4-49cb-b761-9bae564a0a63"
REMOTENESS_TO_QUERY = {
    Remoteness.IN_PERSON: "",
    Remoteness.TEMPORARILY_REMOTE: COVID_REMOTE_MAGIC_STRING,
    Remoteness.PARTIALLY_REMOTE: "",
    Remoteness.FULLY_REMOTE: FULLY_REMOTE_MAGIC_STRING,
    Remoteness.ANY: "",
}
REMOTENESS_STR_MAP = {
    "remote": Remoteness.FULLY_REMOTE,
    "hybrid work": Remoteness.TEMPORARILY_REMOTE,
}


def format_taxonomy_attributes(taxonomy_attributes):
    result = []

    # Loop through the taxonomyAttributes list
    for category in taxonomy_attributes:
        label = category[
            "label"
        ]  # Get the category label (e.g., "job-types", "benefits")
        attributes = category["attributes"]

        # Only process if the attributes list is not empty
        if attributes:
            # Get all attribute labels within the category
            attribute_labels = [attr["label"] for attr in attributes]
            # Create a readable string combining the category label and its attributes
            formatted_str = (
                f"{label.replace('-', ' ').capitalize()}: {', '.join(attribute_labels)}"
            )
            result.append(formatted_str)

    # Join all the formatted strings with a line break or any separator
    return result


class BaseIndeedScraper(BaseScraper):
    """Scrapes jobs from www.indeed.X"""

    def __init__(
        self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter
    ) -> None:
        """Init that contains indeed specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_INDEED_PAGE
        self.query = "+".join(self.config.search_config.keywords)

        # Log if we can't do their remoteness query (Indeed only has 2 lvls.)
        if self.config.search_config.remoteness == Remoteness.PARTIALLY_REMOTE:
            self.logger.warning("Indeed does not support PARTIALLY_REMOTE jobs")

    @property
    def user_agent(self) -> str:
        """Get a randomized user agent for this scraper"""
        return random.choice(USER_AGENT_LIST_MOBILE)

    @property
    def job_get_fields(self) -> str:
        """Call self.get(...) for the JobFields in this list when scraping a Job

        Override this as needed.
        """
        return [
            JobField.TITLE,
            JobField.COMPANY,
            JobField.DESCRIPTION,
            JobField.LOCATION,
            JobField.KEY_ID,
            JobField.TAGS,
            JobField.POST_DATE,
            # JobField.REMOTENESS,
            JobField.WAGE,
        ]

    @property
    def job_set_fields(self) -> str:
        """Call self.set(...) for the JobFields in this list when scraping a Job

        NOTE: Since this passes the Job we are updating, the order of this list
        matters if set fields rely on each-other.

        Override this as needed.
        """
        return [JobField.URL, JobField.REMOTENESS]

    @property
    def delayed_get_set_fields(self) -> str:
        """Delay execution when getting /setting any of these attributes of a
        job.

        Override this as needed.
        """
        return [JobField.RAW]

    @property
    def high_priority_get_set_fields(self) -> List[JobField]:
        """These get() and/or set() fields will be populated first."""
        return [JobField.URL]

    @property
    def headers(self) -> Dict[str, str]:
        """Session header for indeed.X"""
        return {
            "accept": "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, sdch",
            "accept-language": "en-GB,en-US;q=0.8,en;q=0.6",
            "referer": f"https://www.indeed.{self.config.search_config.domain}/",
            "upgrade-insecure-requests": "1",
            "user-agent": self.user_agent,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from a job source into a list of job-soups

        Returns:
            List[BeautifulSoup]: list of jobs soups we can use to make Job init
        """
        # Get the search url
        search_url = self._get_search_url()

        # Parse total results, and calculate the # of pages needed
        pages = self._get_num_search_result_pages(search_url)
        self.logger.info(
            "Found %d pages of search results for query=%s", pages, self.query
        )

        # Init list of job soups
        job_soup_list = []  # type: List[Any]

        # Init threads & futures list FIXME: we should probably delay here too
        threads = ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS)
        try:
            # Scrape soups for all the result pages containing many job listings
            futures = []
            for page in range(0, pages):
                futures.append(
                    threads.submit(
                        self._get_job_soups_from_search_page,
                        search_url,
                        page,
                        job_soup_list,
                    )
                )

            # Wait for all scrape jobs to finish
            wait(futures)

        finally:
            threads.shutdown()

        return job_soup_list

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object that was derived from a JSON string."""

        # Convert BeautifulSoup object back to a dictionary
        job_data = json.loads(soup.text)

        if parameter == JobField.TITLE:
            return job_data.get("displayTitle", None)

        elif parameter == JobField.DESCRIPTION:
            return job_data.get("snippet", None)

        elif parameter == JobField.COMPANY:
            return job_data.get("company", None)

        elif parameter == JobField.LOCATION:
            return job_data.get("formattedLocation", None)

        elif parameter == JobField.TAGS:

            formatted_attributes = format_taxonomy_attributes(
                job_data.get("taxonomyAttributes", [])
            )

            return formatted_attributes

        elif parameter == JobField.REMOTENESS:
            return (
                Remoteness.FULLY_REMOTE
                if job_data.get("remoteLocation", False)
                else Remoteness.UNKNOWN
            )

        elif parameter == JobField.WAGE:
            salary_info = job_data.get("extractedSalary", None)
            if salary_info:
                min_salary = salary_info.get("min")
                max_salary = salary_info.get("max")
                if min_salary and max_salary:
                    return (
                        f"${min_salary} - ${max_salary} {salary_info.get('type', '')}"
                    )
                else:
                    return ""
            return ""

        elif parameter == JobField.POST_DATE:
            return calc_post_date_from_relative_str(
                job_data.get("formattedRelativeTime", None)
            )

        elif parameter == JobField.KEY_ID:
            return job_data.get("jobkey", None)

        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField
        NOTE: URL is high-priority, since we need it to get RAW.
        """
        if parameter == JobField.RAW:
            job._raw_scrape_data = BeautifulSoup(
                self.session.get(job.url).text, self.config.bs4_parser
            )

        elif parameter == JobField.REMOTENESS:
            remoteness = [
                tag.split(":")[-1].strip().lower()
                for tag in job.tags
                if "remote" in tag.lower()
            ]

            if len(remoteness):
                job.remoteness = REMOTENESS_STR_MAP.get(
                    remoteness[0], Remoteness.UNKNOWN
                )

        elif parameter == JobField.DESCRIPTION:
            assert job._raw_scrape_data
            job.description = job._raw_scrape_data.find(
                id="jobDescriptionText"
            ).text.strip()
        elif parameter == JobField.URL:
            assert job.key_id
            job.url = (
                f"https://www.indeed.{self.config.search_config.domain}/m/"
                f"viewjob?jk={job.key_id}"
            )
        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")

    def _get_search_url(self, method: Optional[str] = "get") -> str:
        """Get the indeed search url from SearchTerms
        TODO: use Enum for method instead of str.
        """
        if method == "get":
            return (
                "https://www.indeed.{}/m/jobs?q={}&l={}%2C+{}&radius={}&"
                "limit={}&filter={}{}".format(
                    self.config.search_config.domain,
                    self.query,
                    self.config.search_config.city.replace(
                        " ",
                        "+",
                    ),
                    self.config.search_config.province_or_state.upper(),
                    self._quantize_radius(self.config.search_config.radius),
                    self.max_results_per_page,
                    int(self.config.search_config.return_similar_results),
                    REMOTENESS_TO_QUERY[self.config.search_config.remoteness],
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")

    def _quantize_radius(self, radius: int) -> int:
        """Quantizes the user input radius to a valid radius value into:
        5, 10, 15, 25, 50, 100, and 200 kilometers or miles.
        TODO: implement with numpy instead of if/else cases.
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
        return radius

    def _get_job_soups_from_search_page(
        self, search: str, page: str, job_soup_list: List[BeautifulSoup]
    ) -> None:
        """Scrapes the indeed page for a list of job soups
        NOTE: modifies the job_soup_list in-place
        NOTE: Indeed's remoteness filter sucks, and we will always see a mix.
            ... need to add some kind of filtering for this!
        """
        url = f"{search}&start={page * self.max_results_per_page}"

        try:
            response = self.session.get(url).text
            soup = BeautifulSoup(response, self.config.bs4_parser)

            script_tag = soup.find("script", id="mosaic-data")
            if not script_tag:
                self.logger.warn("No 'mosaic-data' script tag found on the page.")
                return

            script_content = script_tag.string
            json_regex = re.search(
                r'\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});',
                script_content,
                re.DOTALL,
            )

            if json_regex:
                json_data_str = json_regex.group(1)

                try:
                    json_data = json.loads(json_data_str)
                    job_data = (
                        json_data.get("metaData", {})
                        .get("mosaicProviderJobCardsModel", {})
                        .get("results", [])
                    )

                    if job_data:
                        job_data_json = [json.dumps(job) for job in job_data]
                        job_soup_list.extend(
                            [
                                BeautifulSoup(job_json, "lxml")
                                for job_json in job_data_json
                            ]
                        )
                    else:
                        self.logger.error("No job data found in the JSON structure.")
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decoding JSON: {e}")
            else:
                self.logger.error(
                    "No matching job data found in the script tag content."
                )

        except Exception as e:
            self.logger.error(
                f"An error occurred while fetching or parsing the page: {e}"
            )

    def _get_num_search_result_pages(self, search_url: str, max_pages=0) -> int:
        """Calculates the number of pages of job listings to be scraped.

        i.e. your search yields 230 results at 20 res/page -> 12 pages of jobs

        Args:
                        max_pages: the maximum number of pages to be scraped.
        Returns:
            The number of pages to be scraped.
        """
        # Get the html data, initialize bs4 with lxml
        request_html = self.session.get(search_url)
        self.logger.debug("Got Base search results page: %s", search_url)

        query_resp = BeautifulSoup(request_html.text, self.config.bs4_parser)

        num_res = query_resp.find(
            "div", class_="jobsearch-JobCountAndSortPane-jobCount"
        )

        # TODO: we should consider expanding the error cases (scrape error page)
        if not num_res:
            raise ValueError(
                "Unable to identify number of pages of results for query: {}"
                " Please ensure linked page contains results, you may have"
                " provided a city for which there are no results within this"
                " province or state.".format(search_url)
            )

        num_res_text = num_res.get_text().replace(",", "")

        num_res_match = re.search(r"(\d+)\+?\s+jobs", num_res_text)

        if num_res_match:
            num_res = int(num_res_match.group(1))
        else:
            num_res = 0

        number_of_pages = int(ceil(num_res / self.max_results_per_page))
        if max_pages == 0:
            return number_of_pages
        elif number_of_pages < max_pages:
            return number_of_pages
        else:
            return max_pages


class IndeedScraperCANEng(BaseIndeedScraper, BaseCANEngScraper):
    """Scrapes jobs from www.indeed.ca"""


class IndeedScraperUSAEng(BaseIndeedScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.indeed.com"""


class IndeedScraperUKEng(BaseIndeedScraper, BaseUKEngScraper):
    """Scrapes jobs from www.indeed.co.uk"""

    def _get_search_url(self, method: Optional[str] = "get") -> str:
        """Get the indeed search url from SearchTerms
        TODO: use Enum for method instead of str.
        """
        if method == "get":
            return (
                "https://www.indeed.{}/jobs?q={}&l={}&radius={}&"
                "limit={}&filter={}{}".format(
                    self.config.search_config.domain,
                    self.query,
                    self.config.search_config.city.replace(
                        " ",
                        "+",
                    ),
                    self._quantize_radius(self.config.search_config.radius),
                    self.max_results_per_page,
                    int(self.config.search_config.return_similar_results),
                    REMOTENESS_TO_QUERY[self.config.search_config.remoteness],
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")


class IndeedScraperFRFre(BaseIndeedScraper, BaseFRFreScraper):
    """Scrapes jobs from www.indeed.fr"""

    def _get_search_url(self, method: Optional[str] = "get") -> str:
        """Get the indeed search url from SearchTerms
        TODO: use Enum for method instead of str.
        """
        if method == "get":
            return (
                "https://www.indeed.{}/jobs?q={}&l={}+%28{}%29&radius={}&"
                "limit={}&filter={}{}".format(
                    self.config.search_config.domain,
                    self.query,
                    self.config.search_config.city.replace(
                        " ",
                        "+",
                    ),
                    self.config.search_config.province_or_state.upper(),
                    self._quantize_radius(self.config.search_config.radius),
                    self.max_results_per_page,
                    int(self.config.search_config.return_similar_results),
                    REMOTENESS_TO_QUERY[self.config.search_config.remoteness],
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")

    def _get_num_search_result_pages(self, search_url: str, max_pages=0) -> int:
        """Calculates the number of pages of job listings to be scraped.

        i.e. your search yields 230 results at 20 res/page -> 12 pages of jobs

        Args:
                        max_pages: the maximum number of pages to be scraped.
        Returns:
            The number of pages to be scraped.
        """
        # Get the html data, initialize bs4 with lxml
        request_html = self.session.get(search_url)
        self.logger.debug("Got Base search results page: %s", search_url)
        query_resp = BeautifulSoup(request_html.text, self.config.bs4_parser)
        num_res = query_resp.find(id="searchCountPages")
        # TODO: we should consider expanding the error cases (scrape error page)
        if not num_res:
            raise ValueError(
                "Unable to identify number of pages of results for query: {}"
                " Please ensure linked page contains results, you may have"
                " provided a city for which there are no results within this"
                " province or state.".format(search_url)
            )

        num_res = normalize("NFKD", num_res.contents[0].strip())
        num_res = int(re.findall(r"(\d+) ", num_res.replace(",", ""))[1])
        number_of_pages = int(ceil(num_res / self.max_results_per_page))
        if max_pages == 0:
            return number_of_pages
        elif number_of_pages < max_pages:
            return number_of_pages
        else:
            return max_pages


class IndeedScraperDEGer(BaseIndeedScraper, BaseDEGerScraper):
    """Scrapes jobs from de.indeed.com"""

    # The german locale has a different number separators.
    THOUSEP = "."

    def _get_search_url(self, method: Optional[str] = "get") -> str:
        """Get the indeed search url from SearchTerms"""
        if method == "get":
            return (
                # The URL is different to the base scraper because indeed.de is
                # redirecting to de.indeed.com. If the redirect is handled the
                # same URLs can be used.
                "https://{}.indeed.com/jobs?q={}&l={}&radius={}&"
                "limit={}&filter={}{}".format(
                    self.config.search_config.domain,
                    self.query,
                    self.config.search_config.city.replace(
                        " ",
                        "+",
                    ),
                    self._quantize_radius(self.config.search_config.radius),
                    self.max_results_per_page,
                    int(self.config.search_config.return_similar_results),
                    REMOTENESS_TO_QUERY[self.config.search_config.remoteness],
                )
            )
        elif method == "post":
            raise NotImplementedError()
        else:
            raise ValueError(f"No html method {method} exists")

    def _get_num_search_result_pages(self, search_url: str, max_pages=0) -> int:
        """Calculates the number of pages of job listings to be scraped.

        i.e. your search yields 230 results at 50 res/page -> 5 pages of jobs

        Args:
            max_pages: the maximum number of pages to be scraped.
        Returns:
            The number of pages to be scraped.
        """
        # Get the html data, initialize bs4 with lxml
        request_html = self.session.get(search_url)

        query_resp = BeautifulSoup(request_html.text, self.config.bs4_parser)
        num_res = query_resp.find(
            "div", class_="jobsearch-JobCountAndSortPane-jobCount"
        )

        if not num_res:
            raise ValueError(
                "Unable to identify number of pages of results for query: {}"
                " Please ensure linked page contains results, you may have"
                " provided a city for which there are no results within this"
                " province or state.".format(search_url)
            )

        num_res = num_res.contents[0].strip()
        num_res = int(re.findall(r"(\d+)", num_res.replace(self.THOUSEP, ""))[1])
        number_of_pages = int(ceil(num_res / self.max_results_per_page))
        if max_pages == 0:
            return number_of_pages
        elif number_of_pages < max_pages:
            return number_of_pages
        else:
            return max_pages
