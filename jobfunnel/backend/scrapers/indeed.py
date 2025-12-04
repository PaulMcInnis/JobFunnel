"""Scraper designed to get jobs from www.indeed.X using Playwright browser automation"""

import json
import re
from math import ceil
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page, sync_playwright
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
from jobfunnel.resources import JobField, Remoteness

if TYPE_CHECKING:
    from jobfunnel.config import JobFunnelConfigManager

MAX_RESULTS_PER_INDEED_PAGE = 15  # Desktop shows ~15 per page
FULLY_REMOTE_MAGIC_STRING = "&sc=0kf%3Aattr%28DSQF7%29%3B"
REMOTENESS_TO_QUERY: Dict[Remoteness, str] = {
    Remoteness.IN_PERSON: "",
    Remoteness.TEMPORARILY_REMOTE: "",
    Remoteness.PARTIALLY_REMOTE: "",
    Remoteness.FULLY_REMOTE: FULLY_REMOTE_MAGIC_STRING,
    Remoteness.ANY: "",
    Remoteness.UNKNOWN: "",
}
REMOTENESS_STR_MAP = {
    "remote": Remoteness.FULLY_REMOTE,
    "hybrid": Remoteness.PARTIALLY_REMOTE,
}


def format_taxonomy_attributes(taxonomy_attributes):
    """Format taxonomy attributes from Indeed job data into readable tags."""
    result = []
    for category in taxonomy_attributes:
        label = category.get("label", "")
        attributes = category.get("attributes", [])
        if attributes:
            attribute_labels = [attr["label"] for attr in attributes]
            formatted_str = f"{label.replace('-', ' ').capitalize()}: {', '.join(attribute_labels)}"
            result.append(formatted_str)
    return result


class BaseIndeedScraper(BaseScraper):
    """Scrapes jobs from www.indeed.X using Playwright for browser automation"""

    def __init__(self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter) -> None:
        """Init that contains indeed specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_INDEED_PAGE
        self.query = "+".join(self.config.search_config.keywords)
        self._browser: Optional[Browser] = None
        self._playwright = None

        if self.config.search_config.remoteness == Remoteness.PARTIALLY_REMOTE:
            self.logger.warning("Indeed does not support PARTIALLY_REMOTE jobs")

    @property
    def job_get_fields(self) -> List[JobField]:
        """Call self.get(...) for the JobFields in this list when scraping a Job"""
        return [
            JobField.TITLE,
            JobField.COMPANY,
            JobField.DESCRIPTION,
            JobField.LOCATION,
            JobField.KEY_ID,
            JobField.TAGS,
            JobField.POST_DATE,
            JobField.WAGE,
        ]

    @property
    def job_set_fields(self) -> List[JobField]:
        """Call self.set(...) for the JobFields in this list when scraping a Job"""
        return [JobField.URL, JobField.REMOTENESS]

    @property
    def delayed_get_set_fields(self) -> List[JobField]:
        """Delay execution when getting/setting any of these attributes."""
        return []

    @property
    def high_priority_get_set_fields(self) -> List[JobField]:
        """These get()/set() fields will be populated first."""
        return [JobField.URL]

    @property
    def headers(self) -> Dict[str, str]:
        """Session header - not used with Playwright but required by base class."""
        return {}

    def _get_search_url(self) -> str:
        """Get the indeed search url from SearchTerms"""
        remoteness = self.config.search_config.remoteness or Remoteness.UNKNOWN
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        return "https://www.indeed.{}/jobs?q={}&l={}%2C+{}&radius={}{}".format(
            self.config.search_config.domain,
            self.query,
            city.replace(" ", "+"),
            province_or_state.upper(),
            self._quantize_radius(self.config.search_config.radius),
            REMOTENESS_TO_QUERY[remoteness],
        )

    def _quantize_radius(self, radius: int) -> int:
        """Quantizes the user input radius to a valid radius value."""
        if radius < 5:
            return 0
        elif radius < 10:
            return 5
        elif radius < 15:
            return 10
        elif radius < 25:
            return 15
        elif radius < 50:
            return 25
        elif radius < 100:
            return 50
        else:
            return 100

    def _ensure_on_search_results(self, page: Page, search_url: str) -> bool:
        """Ensure we're on search results page, handle CAPTCHA redirect if needed."""
        current_url = page.url
        page_content = page.content()

        # Check if we got redirected away from search (CAPTCHA or homepage)
        if "/jobs?" not in current_url or "verification" in page_content.lower():
            self.logger.info("Not on search results (redirected). Re-navigating to search...")
            page.goto(search_url, timeout=60000)
            page.wait_for_timeout(3000)

            # Check again - if still not on search, CAPTCHA might need solving
            if "verification" in page.content().lower():
                self.logger.info("CAPTCHA detected. Please solve it in the browser...")
                try:
                    page.wait_for_function(
                        "() => !document.body.innerHTML.toLowerCase().includes('verification')",
                        timeout=120000,
                    )
                    # After solving, re-navigate to search
                    page.goto(search_url, timeout=60000)
                    page.wait_for_timeout(2000)
                except Exception:
                    self.logger.warning("CAPTCHA not solved within 120 seconds.")
                    return False
        return True

    def _perform_search_like_human(self, page: Page) -> bool:
        """Navigate to Indeed and perform search like a human user."""
        domain = self.config.search_config.domain
        homepage = f"https://www.indeed.{domain}"

        self.logger.info("Going to Indeed homepage...")
        page.goto(homepage, timeout=60000)
        page.wait_for_timeout(2000)

        # Wait for search box to appear (indicates page loaded properly)
        try:
            page.wait_for_selector('input[id*="what"], input[name*="q"]', timeout=60000)
            self.logger.info("Homepage loaded successfully")
        except Exception:
            self.logger.warning("Could not load homepage search box")
            return False

        # Find and fill the "what" search box
        what_input = page.query_selector('input[id*="what"], input[name*="q"]')
        if what_input:
            what_input.click()
            page.wait_for_timeout(300)
            keywords = " ".join(self.config.search_config.keywords)
            what_input.fill(keywords)
            self.logger.info("Entered keywords: %s", keywords)

        # Find and fill the "where" search box
        where_input = page.query_selector('input[id*="where"], input[name*="l"]')
        if where_input:
            where_input.click()
            page.wait_for_timeout(300)
            # Clear existing location
            where_input.fill("")
            location = f"{self.config.search_config.city}, {self.config.search_config.province_or_state}"
            where_input.fill(location)
            self.logger.info("Entered location: %s", location)

        page.wait_for_timeout(500)

        # Click the search button
        search_btn = page.query_selector('button[type="submit"], button:has-text("Find jobs")')
        if search_btn:
            search_btn.click()
            self.logger.info("Clicked search button")
        else:
            # Try pressing Enter
            page.keyboard.press("Enter")

        # Wait for results to load
        page.wait_for_timeout(3000)
        return True

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from Indeed using Playwright browser automation.

        Returns:
            List[BeautifulSoup]: list of job soups we can use to make Job objects
        """
        job_soup_list = []

        # Use persistent context to save cookies/session between runs
        from pathlib import Path

        user_data_dir = Path(self.config.cache_folder) / "browser_data"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(user_data_dir),
                headless=False,
                viewport={"width": 1280, "height": 900},
                locale="en-CA",
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
                ignore_default_args=["--enable-automation"],
            )
            page = context.pages[0] if context.pages else context.new_page()

            try:
                # Perform search like a human
                if not self._perform_search_like_human(page):
                    raise ValueError("Could not complete search")

                # Get number of pages
                num_pages = self._get_num_search_result_pages_from_page(page)
                self.logger.info(
                    "Found %d pages of search results for query=%s",
                    num_pages,
                    self.query,
                )

                # Scrape first page
                self._extract_jobs_from_page(page, job_soup_list)

                # Scrape remaining pages by clicking Next button
                for page_num in range(1, num_pages):
                    next_btn = page.query_selector('a[data-testid="pagination-page-next"]')
                    if not next_btn:
                        next_btn = page.query_selector('a[aria-label="Next Page"]')
                    if not next_btn:
                        next_btn = page.query_selector('nav a:has-text("Next")')

                    if next_btn:
                        self.logger.info("Clicking Next to go to page %d", page_num + 1)
                        next_btn.click()
                        page.wait_for_timeout(3000)
                        self._extract_jobs_from_page(page, job_soup_list)
                    else:
                        self.logger.warning("No Next button found, stopping pagination")
                        break

            finally:
                context.close()

        return job_soup_list

    def _get_num_search_result_pages_from_page(self, page: Page) -> int:
        """Extract the number of result pages from a loaded page."""
        try:
            # Look for job count in the page
            page_content = page.content()

            # Try to find job count from mosaic-data script
            match = re.search(r'"totalResultCount"\s*:\s*(\d+)', page_content)
            if match:
                total_jobs = int(match.group(1))
                return min(ceil(total_jobs / 15), 5)  # Cap at 5 pages

            # Fallback: look for "X jobs" text
            job_count_el = page.query_selector('[class*="jobCount"]')
            if job_count_el:
                text = job_count_el.text_content()
                if not text:
                    return 1
                match = re.search(r"(\d+)", text.replace(",", ""))
                if match:
                    total_jobs = int(match.group(1))
                    return min(ceil(total_jobs / 15), 5)

            self.logger.warning("Could not determine page count, defaulting to 1")
            return 1

        except Exception as e:
            self.logger.warning("Error getting page count: %s", e)
            return 1

    def _extract_jobs_from_page(self, page: Page, job_soup_list: List[BeautifulSoup]) -> None:
        """Extract job data from a loaded Indeed search results page."""
        page_content = page.content()
        if self.config.debug_scrape:
            self.dump_debug_html(page_content, f"page_{len(job_soup_list)}")
        soup = BeautifulSoup(page_content, self.config.bs4_parser)

        # Try to find mosaic-data script tag with job JSON
        script_tag = soup.find("script", id="mosaic-data")
        if script_tag:
            script_content = script_tag.string or script_tag.get_text()
            if script_content:
                json_regex = re.search(
                    r'\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});',
                    script_content,
                    re.DOTALL,
                )
                if json_regex:
                    try:
                        json_data = json.loads(json_regex.group(1))
                        job_data = (
                            json_data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", [])
                        )
                        if job_data:
                            for job in job_data:
                                job_soup_list.append(BeautifulSoup(json.dumps(job), "lxml"))
                            self.logger.info("Extracted %d jobs from page", len(job_data))
                            return
                    except json.JSONDecodeError as e:
                        self.logger.warning("Error decoding mosaic JSON: %s", e)

        self.logger.warning("Could not extract jobs from mosaic-data on this page")

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object (contains JSON data)."""
        job_data = json.loads(soup.text)

        if parameter == JobField.TITLE:
            return job_data.get("displayTitle") or job_data.get("title")

        elif parameter == JobField.DESCRIPTION:
            return job_data.get("snippet", "")

        elif parameter == JobField.COMPANY:
            return job_data.get("company", "")

        elif parameter == JobField.LOCATION:
            return job_data.get("formattedLocation", "")

        elif parameter == JobField.TAGS:
            return format_taxonomy_attributes(job_data.get("taxonomyAttributes", []))

        elif parameter == JobField.WAGE:
            salary_info = job_data.get("extractedSalary")
            if salary_info:
                min_sal = salary_info.get("min")
                max_sal = salary_info.get("max")
                sal_type = salary_info.get("type", "")
                if min_sal and max_sal:
                    return f"${min_sal} - ${max_sal} {sal_type}"
            return ""

        elif parameter == JobField.POST_DATE:
            rel_time = job_data.get("formattedRelativeTime", "")
            if rel_time:
                return calc_post_date_from_relative_str(rel_time)
            return None

        elif parameter == JobField.KEY_ID:
            return job_data.get("jobkey", "")

        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField."""
        if parameter == JobField.URL:
            job.url = f"https://www.indeed.{self.config.search_config.domain}/viewjob?jk={job.key_id or ''}"

        elif parameter == JobField.REMOTENESS:
            remoteness_list = [tag.split(":")[-1].strip().lower() for tag in job.tags if "remote" in tag.lower()]
            if remoteness_list:
                job.remoteness = REMOTENESS_STR_MAP.get(remoteness_list[0], Remoteness.UNKNOWN)

        elif parameter == JobField.RAW:
            # Skip fetching raw page to avoid extra requests
            pass

        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")


class IndeedScraperCANEng(BaseIndeedScraper, BaseCANEngScraper):
    """Scrapes jobs from www.indeed.ca"""


class IndeedScraperUSAEng(BaseIndeedScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.indeed.com"""


class IndeedScraperUKEng(BaseIndeedScraper, BaseUKEngScraper):
    """Scrapes jobs from www.indeed.co.uk"""

    def _get_search_url(self) -> str:
        """Get the indeed.co.uk search url."""
        remoteness = self.config.search_config.remoteness or Remoteness.UNKNOWN
        city = self.config.search_config.city or ""
        return "https://www.indeed.{}/jobs?q={}&l={}&radius={}{}".format(
            self.config.search_config.domain,
            self.query,
            city.replace(" ", "+"),
            self._quantize_radius(self.config.search_config.radius),
            REMOTENESS_TO_QUERY[remoteness],
        )


class IndeedScraperFRFre(BaseIndeedScraper, BaseFRFreScraper):
    """Scrapes jobs from www.indeed.fr"""

    def _get_search_url(self) -> str:
        """Get the indeed.fr search url."""
        remoteness = self.config.search_config.remoteness or Remoteness.UNKNOWN
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        return "https://www.indeed.{}/jobs?q={}&l={}+%28{}%29&radius={}{}".format(
            self.config.search_config.domain,
            self.query,
            city.replace(" ", "+"),
            province_or_state.upper(),
            self._quantize_radius(self.config.search_config.radius),
            REMOTENESS_TO_QUERY[remoteness],
        )


class IndeedScraperDEGer(BaseIndeedScraper, BaseDEGerScraper):
    """Scrapes jobs from de.indeed.com"""

    def _get_search_url(self) -> str:
        """Get the de.indeed.com search url."""
        remoteness = self.config.search_config.remoteness or Remoteness.UNKNOWN
        city = self.config.search_config.city or ""
        return "https://{}.indeed.com/jobs?q={}&l={}&radius={}{}".format(
            self.config.search_config.domain,
            self.query,
            city.replace(" ", "+"),
            self._quantize_radius(self.config.search_config.radius),
            REMOTENESS_TO_QUERY[remoteness],
        )
