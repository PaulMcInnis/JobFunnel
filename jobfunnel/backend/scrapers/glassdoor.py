"""Scraper for www.glassdoor.X using Playwright browser automation"""

import json
from math import ceil
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page, sync_playwright
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
from jobfunnel.resources import JobField

# pylint: disable=using-constant-test,unused-import
if False:  # or typing.TYPE_CHECKING  if python3.5.3+
    from jobfunnel.config import JobFunnelConfigManager
# pylint: enable=using-constant-test,unused-import


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
    """Scrapes jobs from www.glassdoor.X using Playwright for browser automation"""

    def __init__(
        self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter
    ) -> None:
        """Init that contains glassdoor specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_GLASSDOOR_PAGE
        self.query = " ".join(self.config.search_config.keywords)
        self._browser: Optional[Browser] = None
        self._playwright = None

    @property
    def job_get_fields(self) -> List[JobField]:
        """Call self.get(...) for the JobFields in this list when scraping a Job"""
        return [
            JobField.TITLE,
            JobField.COMPANY,
            JobField.LOCATION,
            JobField.KEY_ID,
            JobField.URL,
            JobField.WAGE,
            JobField.POST_DATE,
        ]

    @property
    def job_set_fields(self) -> List[JobField]:
        """Call self.set(...) for the JobFields in this list when scraping a Job"""
        return [JobField.DESCRIPTION]

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

    def quantize_radius(self, radius: int) -> int:
        """Get the glassdoor-quantized radius. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement quantize_radius")

    def _perform_search_like_human(self, page: Page) -> bool:
        """Navigate to Glassdoor and perform search like a human user."""
        domain = self.config.search_config.domain
        homepage = f"https://www.glassdoor.{domain}"

        self.logger.info("Going to Glassdoor homepage...")
        page.goto(homepage, timeout=60000)
        page.wait_for_timeout(2000)

        # Wait for search box to appear
        try:
            page.wait_for_selector(
                'input[id*="keyword"], input[name*="keyword"], input[placeholder*="Job"]',
                timeout=60000,
            )
            self.logger.info("Homepage loaded successfully")
        except Exception:
            self.logger.warning("Could not load homepage search box")
            return False

        # Find and fill the keyword search box
        keyword_input = page.query_selector(
            'input[id*="keyword"], input[name*="keyword"], input[placeholder*="Job"]'
        )
        if keyword_input:
            keyword_input.click()
            page.wait_for_timeout(300)
            keyword_input.fill(self.query)
            self.logger.info("Entered keywords: %s", self.query)

        # Find and fill the location search box
        location_input = page.query_selector(
            'input[id*="location"], input[name*="location"], input[placeholder*="Location"]'
        )
        if location_input:
            location_input.click()
            page.wait_for_timeout(300)
            # Clear existing location
            location_input.fill("")
            location = f"{self.config.search_config.city}, {self.config.search_config.province_or_state}"
            location_input.fill(location)
            self.logger.info("Entered location: %s", location)

        page.wait_for_timeout(500)

        # Click the search button
        search_btn = page.query_selector(
            'button[type="submit"], button[data-test="search-bar-submit"]'
        )
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
        """Scrapes raw data from Glassdoor using Playwright browser automation.

        Returns:
            List[BeautifulSoup]: list of job soups we can use to make Job objects
        """
        job_soup_list = []

        # Use persistent context to save cookies/session between runs
        from pathlib import Path

        user_data_dir = Path(self.config.cache_folder) / "browser_data_glassdoor"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(user_data_dir),
                headless=False,
                viewport={"width": 1280, "height": 900},
                locale="en-US",
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
                    next_btn = page.query_selector(
                        'button[data-test="pagination-next"]'
                    )
                    if not next_btn:
                        next_btn = page.query_selector('a[data-test="pagination-next"]')
                    if not next_btn:
                        next_btn = page.query_selector('button:has-text("Next")')
                    if not next_btn:
                        next_btn = page.query_selector('a:has-text("Next")')

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
            page_content = page.content()

            # Try to find job count from page content
            match = re.search(r'"jobListingSearchTotalCount"\s*:\s*(\d+)', page_content)
            if match:
                total_jobs = int(match.group(1))
                return min(ceil(total_jobs / self.max_results_per_page), 5)

            # Fallback: look for "X jobs" text
            job_count_el = page.query_selector('[data-test="jobCount"]')
            if job_count_el:
                text = job_count_el.text_content() or ""
                match = re.search(r"(\d+)", text.replace(",", ""))
                if match:
                    total_jobs = int(match.group(1))
                    return min(ceil(total_jobs / self.max_results_per_page), 5)

            self.logger.warning("Could not determine page count, defaulting to 1")
            return 1

        except Exception as e:
            self.logger.warning("Error getting page count: %s", e)
            return 1

    def _extract_jobs_from_page(
        self, page: Page, job_soup_list: List[BeautifulSoup]
    ) -> None:
        """Extract job data from a loaded Glassdoor search results page."""
        page_content = page.content()
        soup = BeautifulSoup(page_content, self.config.bs4_parser)

        # Try to find job data in JSON script tags
        script_tags = soup.find_all("script", type="application/json")
        for script_tag in script_tags:
            try:
                script_content = script_tag.string or script_tag.get_text()
                if script_content and "jobListings" in script_content:
                    json_data = json.loads(script_content)
                    job_listings = self._find_job_listings_in_json(json_data)
                    if job_listings:
                        for job in job_listings:
                            job_soup_list.append(BeautifulSoup(json.dumps(job), "lxml"))
                        self.logger.info(
                            "Extracted %d jobs from page", len(job_listings)
                        )
                        return
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback: Try to find job cards in HTML
        job_cards = soup.find_all("li", attrs={"data-test": "jobListing"})
        if not job_cards:
            job_cards = soup.find_all("li", class_=re.compile(r"job.*listing", re.I))

        if job_cards:
            for card in job_cards:
                job_soup_list.append(BeautifulSoup(str(card), self.config.bs4_parser))
            self.logger.info("Extracted %d jobs from HTML", len(job_cards))
        else:
            self.logger.warning("Could not extract jobs from this page")

    def _find_job_listings_in_json(self, data: Any) -> List[Dict]:
        """Recursively search for job listings in JSON data."""
        if isinstance(data, dict):
            if "jobListings" in data:
                listings = data["jobListings"]
                if isinstance(listings, list):
                    return listings
                if isinstance(listings, dict) and "jobListings" in listings:
                    return listings["jobListings"]
            for value in data.values():
                result = self._find_job_listings_in_json(value)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_job_listings_in_json(item)
                if result:
                    return result
        return []

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object."""
        # Try to parse as JSON first (from script tag extraction)
        try:
            job_data = json.loads(soup.text)
            return self._get_from_json(parameter, job_data)
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback to HTML parsing
        return self._get_from_html(parameter, soup)

    def _get_from_json(self, parameter: JobField, job_data: Dict) -> Any:
        """Get job attribute from JSON data."""
        # Handle nested job structure
        job = job_data.get("jobview", job_data.get("job", job_data))

        if parameter == JobField.TITLE:
            return job.get("jobTitleText") or job.get("title") or job.get("jobTitle")

        elif parameter == JobField.COMPANY:
            employer = job.get("employer", {})
            if isinstance(employer, dict):
                return employer.get("name", "")
            return job.get("employerName", "")

        elif parameter == JobField.LOCATION:
            location = job.get("location", {})
            if isinstance(location, dict):
                return location.get("locationName") or location.get("name", "")
            return job.get("locationName", "")

        elif parameter == JobField.KEY_ID:
            return str(
                job.get("listingId") or job.get("jobListingId") or job.get("id", "")
            )

        elif parameter == JobField.URL:
            job_url = job.get("jobViewUrl") or job.get("seoJobLink") or job.get("url")
            if job_url:
                if not job_url.startswith("http"):
                    return f"https://www.glassdoor.{self.config.search_config.domain}{job_url}"
                return job_url
            # Construct URL from ID
            key_id = self._get_from_json(JobField.KEY_ID, job_data)
            if key_id:
                return f"https://www.glassdoor.{self.config.search_config.domain}/job-listing/?jl={key_id}"
            return ""

        elif parameter == JobField.WAGE:
            salary = job.get("salarySnippet") or job.get("salary", {})
            if isinstance(salary, dict):
                return salary.get("text") or salary.get("salaryText", "")
            return str(salary) if salary else ""

        elif parameter == JobField.POST_DATE:
            age_str = job.get("ageInDays") or job.get("listingAge")
            if age_str is not None:
                return calc_post_date_from_relative_str(f"{age_str} days")
            date_str = job.get("discoverDate") or job.get("postedDate")
            if date_str:
                return calc_post_date_from_relative_str(date_str)
            return None

        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def _get_from_html(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get job attribute from HTML soup."""
        if parameter == JobField.TITLE:
            title_el = soup.find(attrs={"data-test": "job-title"})
            if title_el:
                return title_el.get_text(strip=True)
            title_el = soup.find("a", class_=re.compile(r"job.*title", re.I))
            return title_el.get_text(strip=True) if title_el else ""

        elif parameter == JobField.COMPANY:
            company_el = soup.find(attrs={"data-test": "employer-name"})
            if company_el:
                return company_el.get_text(strip=True)
            company_el = soup.find(class_=re.compile(r"employer.*name", re.I))
            return company_el.get_text(strip=True) if company_el else ""

        elif parameter == JobField.LOCATION:
            loc_el = soup.find(attrs={"data-test": "job-location"})
            if loc_el:
                return loc_el.get_text(strip=True)
            loc_el = soup.find(class_=re.compile(r"location", re.I))
            return loc_el.get_text(strip=True) if loc_el else ""

        elif parameter == JobField.KEY_ID:
            # Try data attributes
            job_id = soup.get("data-id") or soup.get("data-job-id")
            if job_id:
                return str(job_id)
            # Try finding from link
            link = soup.find("a", href=re.compile(r"jl=(\d+)"))
            if link:
                href = link.get("href")
                if href and isinstance(href, str):
                    match = re.search(r"jl=(\d+)", href)
                    if match:
                        return match.group(1)
            return ""

        elif parameter == JobField.URL:
            link = soup.find("a", attrs={"data-test": "job-link"})
            if not link:
                link = soup.find("a", href=re.compile(r"/job-listing/"))
            if link:
                href = link.get("href")
                if href and isinstance(href, str):
                    if not href.startswith("http"):
                        return f"https://www.glassdoor.{self.config.search_config.domain}{href}"
                    return href
            return ""

        elif parameter == JobField.WAGE:
            salary_el = soup.find(attrs={"data-test": "detailSalary"})
            if salary_el:
                return salary_el.get_text(strip=True)
            salary_el = soup.find(class_=re.compile(r"salary", re.I))
            return salary_el.get_text(strip=True) if salary_el else ""

        elif parameter == JobField.POST_DATE:
            date_el = soup.find(attrs={"data-test": "job-age"})
            if date_el:
                return calc_post_date_from_relative_str(date_el.get_text(strip=True))
            date_el = soup.find(class_=re.compile(r"posted|age|date", re.I))
            if date_el:
                return calc_post_date_from_relative_str(date_el.get_text(strip=True))
            return None

        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField."""
        if parameter == JobField.DESCRIPTION:
            # Description would require loading the job page
            # Skip for now to avoid extra requests
            job.description = ""

        elif parameter == JobField.RAW:
            # Skip fetching raw page
            pass

        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")


class GlassDoorMetricRadius:
    """Metric units shared by GlassDoorScraperCANEng and GlassDoorScraperUKEng"""

    def quantize_radius(self, radius: int) -> int:
        """Convert radius to km."""
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
        """Get a USA radius (miles)."""
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
