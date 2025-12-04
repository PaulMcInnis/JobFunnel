"""Scraper designed to get jobs from www.simplyhired.X using Playwright browser automation"""

import re
from math import ceil
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, Page, sync_playwright
from requests import Session

from jobfunnel.backend import Job
from jobfunnel.backend.scrapers.base import (
    BaseCANEngScraper,
    BaseScraper,
    BaseUSAEngScraper,
)
from jobfunnel.backend.tools.filters import JobFilter
from jobfunnel.backend.tools.tools import calc_post_date_from_relative_str
from jobfunnel.resources import JobField, Remoteness

if TYPE_CHECKING:
    from jobfunnel.config import JobFunnelConfigManager

MAX_RESULTS_PER_SIMPLYHIRED_PAGE = 20


class BaseSimplyHiredScraper(BaseScraper):
    """Scrapes jobs from www.simplyhired.X using Playwright for browser automation"""

    def __init__(self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter) -> None:
        """Init that contains SimplyHired specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_SIMPLYHIRED_PAGE
        self.query = "+".join(self.config.search_config.keywords)
        self._browser: Optional[Browser] = None
        self._playwright = None

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
        """Get the SimplyHired search url from SearchTerms"""
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        return "https://www.simplyhired.{}/search?q={}&l={}%2C+{}".format(
            self.config.search_config.domain,
            self.query,
            city.replace(" ", "+"),
            province_or_state.upper(),
        )

    def _perform_search_like_human(self, page: Page) -> bool:
        """Navigate to SimplyHired and perform search like a human user."""
        domain = self.config.search_config.domain
        homepage = f"https://www.simplyhired.{domain}"

        self.logger.info("Going to SimplyHired homepage...")
        page.goto(homepage, timeout=60000)
        page.wait_for_timeout(2000)

        # Wait for search box to appear
        try:
            page.wait_for_selector('input[name="q"], input[id*="what"]', timeout=60000)
            self.logger.info("Homepage loaded successfully")
        except Exception:
            self.logger.warning("Could not load homepage search box")
            return False

        # Find and fill the "what" search box
        what_input = page.query_selector('input[name="q"], input[id*="what"]')
        if what_input:
            what_input.click()
            page.wait_for_timeout(300)
            keywords = " ".join(self.config.search_config.keywords)
            what_input.fill(keywords)
            self.logger.info("Entered keywords: %s", keywords)

        # Find and fill the "where" search box
        where_input = page.query_selector('input[name="l"], input[id*="where"]')
        if where_input:
            where_input.click()
            page.wait_for_timeout(300)
            where_input.fill("")
            # For remote jobs, search "remote" in location field
            if self.config.search_config.remoteness == Remoteness.FULLY_REMOTE:
                location = "remote"
            else:
                location = f"{self.config.search_config.city}, {self.config.search_config.province_or_state}"
            where_input.fill(location)
            self.logger.info("Entered location: %s", location)

        page.wait_for_timeout(500)

        # Click the search button
        search_btn = page.query_selector('button[type="submit"], button:has-text("Find Jobs")')
        if search_btn:
            search_btn.click()
            self.logger.info("Clicked search button")
        else:
            page.keyboard.press("Enter")

        page.wait_for_timeout(3000)
        return True

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from SimplyHired using Playwright browser automation.

        Returns:
            List[BeautifulSoup]: list of job soups we can use to make Job objects
        """
        job_soup_list = []

        from pathlib import Path

        user_data_dir = Path(self.config.cache_folder) / "browser_data_simplyhired"
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
                if not self._perform_search_like_human(page):
                    raise ValueError("Could not complete search")

                num_pages = self._get_num_search_result_pages_from_page(page)
                self.logger.info(
                    "Found %d pages of search results for query=%s",
                    num_pages,
                    self.query,
                )

                # Scrape first page
                self._extract_jobs_from_page(page, job_soup_list)

                # Scrape remaining pages
                for page_num in range(1, num_pages):
                    next_btn = page.query_selector('a[data-testid="pageNumberBlockNext"]')
                    if not next_btn:
                        next_btn = page.query_selector('a[aria-label="Next page"]')

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

            # Look for job count text like "X jobs"
            match = re.search(r"(\d+[\d,]*)\s*jobs?", page_content, re.IGNORECASE)
            if match:
                total_jobs = int(match.group(1).replace(",", ""))
                return min(ceil(total_jobs / MAX_RESULTS_PER_SIMPLYHIRED_PAGE), 5)

            self.logger.warning("Could not determine page count, defaulting to 1")
            return 1

        except Exception as e:
            self.logger.warning("Error getting page count: %s", e)
            return 1

    def _extract_jobs_from_page(self, page: Page, job_soup_list: List[BeautifulSoup]) -> None:
        """Extract job data from a loaded SimplyHired search results page."""
        page_content = page.content()
        if self.config.debug_scrape:
            self.dump_debug_html(page_content, f"page_{len(job_soup_list)}")
        soup = BeautifulSoup(page_content, self.config.bs4_parser)

        # SimplyHired uses divs with data-testid="searchSerpJob" and data-jobkey attribute
        job_cards = soup.find_all("div", {"data-testid": "searchSerpJob"})
        if not job_cards:
            # Fallback: look for divs with data-jobkey
            job_cards = soup.find_all("div", {"data-jobkey": True})

        if job_cards:
            for card in job_cards:
                job_soup_list.append(BeautifulSoup(str(card), self.config.bs4_parser))
            self.logger.info("Extracted %d jobs from page", len(job_cards))
        else:
            self.logger.warning("Could not extract jobs from this page")

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object."""
        if parameter == JobField.TITLE:
            # Look for h2 with data-testid="searchSerpJobTitle"
            title_el = soup.find("h2", {"data-testid": "searchSerpJobTitle"})
            if not title_el:
                title_el = soup.find("h2")
            return title_el.get_text(strip=True) if title_el else ""

        elif parameter == JobField.COMPANY:
            # Look for span with data-testid="companyName"
            company_el = soup.find("span", {"data-testid": "companyName"})
            return company_el.get_text(strip=True) if company_el else ""

        elif parameter == JobField.DESCRIPTION:
            # SimplyHired search results don't have full descriptions, use requirement chips
            chips = soup.find_all(attrs={"data-testid": re.compile(r"requirementChip-\d+")})
            if chips:
                return "Requirements: " + ", ".join(c.get_text(strip=True) for c in chips)
            return "No description available"

        elif parameter == JobField.LOCATION:
            # Look for span with data-testid="searchSerpJobLocation"
            loc_el = soup.find("span", {"data-testid": "searchSerpJobLocation"})
            return loc_el.get_text(strip=True) if loc_el else ""

        elif parameter == JobField.TAGS:
            tags = []
            tag_els = soup.find_all(class_=re.compile(r"tag|badge|benefit", re.IGNORECASE))
            for tag in tag_els:
                tags.append(tag.get_text(strip=True))
            return tags

        elif parameter == JobField.WAGE:
            # Look for salary with data-testid="searchSerpJobSalaryConfirmed"
            salary_el = soup.find(attrs={"data-testid": "searchSerpJobSalaryConfirmed"})
            return salary_el.get_text(strip=True) if salary_el else ""

        elif parameter == JobField.POST_DATE:
            # Look for date stamp with data-testid="searchSerpJobDateStamp"
            date_el = soup.find(attrs={"data-testid": "searchSerpJobDateStamp"})
            if date_el:
                rel_time = date_el.get_text(strip=True)
                return calc_post_date_from_relative_str(rel_time)
            return None

        elif parameter == JobField.KEY_ID:
            # Try data-jobkey attribute first
            job_key = soup.get("data-jobkey")
            if job_key and isinstance(job_key, str):
                return job_key
            # Fallback: extract from link
            link = soup.find("a", href=re.compile(r"/job/"))
            if link:
                href = link.get("href", "")
                if isinstance(href, str):
                    match = re.search(r"/job/([^/?]+)", href)
                    if match:
                        return match.group(1)
            return ""

        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField."""
        if parameter == JobField.URL:
            link = soup.find("a", href=re.compile(r"/job/"))
            if link:
                href = link.get("href", "")
                if isinstance(href, str):
                    if href.startswith("/"):
                        job.url = f"https://www.simplyhired.{self.config.search_config.domain}{href}"
                    else:
                        job.url = href
                else:
                    job.url = f"https://www.simplyhired.{self.config.search_config.domain}/job/{job.key_id or ''}"
            else:
                job.url = f"https://www.simplyhired.{self.config.search_config.domain}/job/{job.key_id or ''}"

        elif parameter == JobField.REMOTENESS:
            text = soup.get_text().lower()
            if "remote" in text:
                job.remoteness = Remoteness.FULLY_REMOTE
            elif "hybrid" in text:
                job.remoteness = Remoteness.PARTIALLY_REMOTE
            else:
                job.remoteness = Remoteness.UNKNOWN

        elif parameter == JobField.RAW:
            pass

        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")


class SimplyHiredScraperCANEng(BaseSimplyHiredScraper, BaseCANEngScraper):
    """Scrapes jobs from www.simplyhired.ca"""


class SimplyHiredScraperUSAEng(BaseSimplyHiredScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.simplyhired.com"""
