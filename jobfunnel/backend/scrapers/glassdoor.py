"""Scraper designed to get jobs from www.glassdoor.com using Playwright browser automation.

Glassdoor requires authentication. If not logged in, the scraper will open a browser
window for the user to log in manually, then save the session for future use.
JobFunnel never stores or transmits user credentials - only session cookies.
"""

import re
import shutil
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
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
from jobfunnel.resources import JobField, Remoteness

if TYPE_CHECKING:
    from jobfunnel.config import JobFunnelConfigManager

MAX_RESULTS_PER_GLASSDOOR_PAGE = 30

# Glassdoor location IDs for major regions (used in URL construction)
# These are approximate and Glassdoor will expand search to nearby areas
GLASSDOOR_LOCATION_IDS = {
    # USA
    "USA": "1",
    # Canada
    "CANADA": "3",
    # UK
    "UK": "2",
}


class BaseGlassdoorScraper(BaseScraper):
    """Scrapes jobs from www.glassdoor.com using Playwright for browser automation.

    Uses a persistent browser context to maintain login state between runs.
    If not logged in, will prompt user to log in manually in the browser window.
    """

    def __init__(self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter) -> None:
        """Init that contains Glassdoor specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_GLASSDOOR_PAGE
        self.query = " ".join(self.config.search_config.keywords)
        self._browser: Optional[Browser] = None
        self._playwright = None

        # Set up persistent browser data directory for maintaining login
        self._user_data_dir = Path(self.config.cache_folder) / "browser_data_glassdoor"
        self._user_data_dir.mkdir(parents=True, exist_ok=True)

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
        """Get the Glassdoor jobs search URL."""
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        location = f"{city}, {province_or_state}".strip(", ")

        # Glassdoor search URL format
        base_url = "https://www.glassdoor.com/Job/jobs.htm"
        params = [
            f"sc.keyword={self.query.replace(' ', '%20')}",
            f"locT=C",  # Location type: City
            f"locKeyword={location.replace(' ', '%20').replace(',', '%2C')}",
        ]

        # Add radius filter if specified
        radius = self.config.search_config.radius
        if radius:
            params.append(f"radius={radius}")

        return f"{base_url}?{'&'.join(params)}"

    def _check_login_status(self, page: Page) -> bool:
        """Check if we're logged in to Glassdoor."""
        try:
            # Check URL - if we're on login page, not logged in
            if "/member/" in page.url or "/login" in page.url:
                return False

            # Check for elements that indicate we're logged in
            # Profile icon or user menu appears when logged in
            profile = page.query_selector('[data-test="profile-icon"], [class*="profileIcon"]')
            if profile:
                return True

            # Check for sign-in link (means NOT logged in)
            signin = page.query_selector('a[href*="signIn"], button[data-test="sign-in"]')
            if signin:
                return False

            # Check for job results - if we can see jobs, we might be logged in
            jobs = page.query_selector('[data-test="jobListing"], [class*="JobCard"]')
            if jobs:
                return True

            return False
        except Exception:
            return False

    def _wait_for_manual_login(self, page: Page, context: BrowserContext) -> bool:
        """Wait for user to manually log in to Glassdoor.

        Returns True if login successful, False if timed out or failed.
        """
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("  Glassdoor Login Required")
        self.logger.info("=" * 60)
        self.logger.info("")
        self.logger.info("Please log in to Glassdoor in the browser window.")
        self.logger.info("Complete any 2FA/CAPTCHA if required.")
        self.logger.info("The scraper will continue automatically once logged in.")
        self.logger.info("")
        self.logger.info("Waiting for login (timeout: 5 minutes)...")

        # Navigate to login page
        page.goto("https://www.glassdoor.com/profile/login_input.htm", timeout=60000)

        # Wait for login to complete (check every 2 seconds for 5 minutes)
        max_wait_seconds = 300
        check_interval = 2
        elapsed = 0

        while elapsed < max_wait_seconds:
            page.wait_for_timeout(check_interval * 1000)
            elapsed += check_interval

            # Check if we're now logged in
            if self._check_login_status(page):
                self.logger.info("Login successful!")
                return True

            # Also check if we're on homepage or jobs page after login
            if "/index" in page.url or "/Job/" in page.url:
                self.logger.info("Login successful!")
                return True

        self.logger.error("Login timed out after 5 minutes.")
        return False

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from Glassdoor using Playwright browser automation.

        Returns:
            List[BeautifulSoup]: list of job soups we can use to make Job objects
        """
        job_soup_list: List[BeautifulSoup] = []

        # Clear browser data if force_login is set
        if self.config.force_login and self._user_data_dir.exists():
            self.logger.info("Force login requested, clearing browser data...")
            shutil.rmtree(self._user_data_dir)
            self._user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            # Use persistent context to maintain login between runs
            context = p.chromium.launch_persistent_context(
                str(self._user_data_dir),
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
                # Navigate to Glassdoor jobs search
                search_url = self._get_search_url()
                self.logger.info("Navigating to Glassdoor jobs: %s", search_url)
                page.goto(search_url, timeout=60000)
                page.wait_for_timeout(3000)

                # Check if we're logged in, prompt for login if not
                if not self._check_login_status(page):
                    self.logger.info("Not logged in to Glassdoor, prompting for login...")
                    if not self._wait_for_manual_login(page, context):
                        raise ValueError("Glassdoor login required but not completed.")

                    # Navigate back to search after login
                    page.goto(search_url, timeout=60000)
                    page.wait_for_timeout(3000)

                # Wait for job listings to load
                try:
                    page.wait_for_selector(
                        '[data-test="jobListing"], [class*="JobCard"], [class*="jobCard"]',
                        timeout=30000,
                    )
                except Exception:
                    self.logger.warning("Could not find job listings, page may have changed")

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
                    # Glassdoor uses pagination with page numbers
                    next_btn = page.query_selector('button[data-test="pagination-next"]')
                    if not next_btn:
                        next_btn = page.query_selector('button[aria-label*="Next"]')
                    if not next_btn:
                        next_btn = page.query_selector('a[data-test="pagination-link-next"]')

                    if next_btn:
                        self.logger.info("Clicking to go to page %d", page_num + 1)
                        next_btn.click()
                        page.wait_for_timeout(3000)
                        self._extract_jobs_from_page(page, job_soup_list)
                    else:
                        # Try scrolling to load more jobs
                        self.logger.info("Scrolling to load more jobs...")
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(2000)
                        new_jobs_before = len(job_soup_list)
                        self._extract_jobs_from_page(page, job_soup_list)
                        if len(job_soup_list) == new_jobs_before:
                            self.logger.info("No more jobs to load")
                            break

            finally:
                context.close()

        return job_soup_list

    def _get_num_search_result_pages_from_page(self, page: Page) -> int:
        """Extract the number of result pages from a loaded page."""
        try:
            page_content = page.content()

            # Look for job count text like "X jobs"
            match = re.search(r"([\d,]+)\s*jobs?", page_content, re.IGNORECASE)
            if match:
                total_jobs = int(match.group(1).replace(",", ""))
                return min(ceil(total_jobs / MAX_RESULTS_PER_GLASSDOOR_PAGE), 5)

            # Look for pagination info
            pagination = page.query_selector('[data-test="pagination"]')
            if pagination:
                page_buttons = pagination.query_selector_all("button, a")
                if page_buttons:
                    return min(len(page_buttons), 5)

            self.logger.warning("Could not determine page count, defaulting to 1")
            return 1

        except Exception as e:
            self.logger.warning("Error getting page count: %s", e)
            return 1

    def _extract_jobs_from_page(self, page: Page, job_soup_list: List[BeautifulSoup]) -> None:
        """Extract job data from a loaded Glassdoor search results page."""
        page_content = page.content()
        if self.config.debug_scrape:
            self.dump_debug_html(page_content, f"page_{len(job_soup_list)}")
        soup = BeautifulSoup(page_content, self.config.bs4_parser)

        # Glassdoor job cards - try multiple selectors
        # First try elements with data-jobid attribute
        job_cards = soup.find_all(attrs={"data-jobid": True})
        if not job_cards:
            job_cards = soup.find_all("li", {"data-test": "jobListing"})
        if not job_cards:
            job_cards = soup.find_all("div", class_=re.compile(r"JobCard|jobCard"))
        if not job_cards:
            job_cards = soup.find_all("li", class_=re.compile(r"react-job-listing"))
        if not job_cards:
            # Try finding cards by job link pattern
            job_links = soup.find_all("a", href=re.compile(r"/job-listing/|/partner/jobListing"))
            job_cards = [link.find_parent("li") or link.find_parent("div") for link in job_links]
            job_cards = [c for c in job_cards if c]

        existing_ids = {
            self._extract_job_id_from_soup(BeautifulSoup(str(s), self.config.bs4_parser)) for s in job_soup_list
        }

        if job_cards:
            new_count = 0
            for card in job_cards:
                card_soup = BeautifulSoup(str(card), self.config.bs4_parser)
                job_id = self._extract_job_id_from_soup(card_soup)
                if job_id and job_id not in existing_ids:
                    job_soup_list.append(card_soup)
                    existing_ids.add(job_id)
                    new_count += 1
            self.logger.info("Extracted %d new jobs from page", new_count)
        else:
            self.logger.warning("Could not extract jobs from this page")

    def _extract_job_id_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract job ID from a job card soup."""
        # Try data-jobid attribute (Glassdoor's current format)
        job_id_el = soup.find(attrs={"data-jobid": True})
        if job_id_el:
            return str(job_id_el.get("data-jobid", ""))

        # Try data-id or data-job-id attribute
        job_id_el = soup.find(attrs={"data-id": True})
        if job_id_el:
            return str(job_id_el.get("data-id", ""))

        job_id_el = soup.find(attrs={"data-job-id": True})
        if job_id_el:
            return str(job_id_el.get("data-job-id", ""))

        # Try extracting from job link
        link = soup.find("a", href=re.compile(r"/job-listing/|jobListingId="))
        if link:
            href = link.get("href", "")
            if isinstance(href, str):
                # Try pattern like /job-listing/title-123456
                match = re.search(r"-(\d{6,})", href)
                if match:
                    return match.group(1)
                # Try jobListingId param
                match = re.search(r"jobListingId=(\d+)", href)
                if match:
                    return match.group(1)

        return ""

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object."""
        if parameter == JobField.TITLE:
            # Glassdoor uses JobCard_jobTitle__* class
            title_el = soup.find(class_=re.compile(r"JobCard_jobTitle"))
            if not title_el:
                title_el = soup.find(attrs={"data-test": "job-title"})
            if not title_el:
                title_el = soup.find(class_=re.compile(r"jobTitle|JobTitle"))
            return title_el.get_text(strip=True) if title_el else ""

        elif parameter == JobField.COMPANY:
            # Glassdoor uses EmployerProfile_compactEmployerName__* class
            company_el = soup.find(class_=re.compile(r"EmployerProfile_compactEmployerName"))
            if not company_el:
                company_el = soup.find(attrs={"data-test": "employer-name"})
            if not company_el:
                company_el = soup.find(class_=re.compile(r"employerName|EmployerName"))
            return company_el.get_text(strip=True) if company_el else ""

        elif parameter == JobField.DESCRIPTION:
            # Glassdoor search results have limited description
            desc_el = soup.find(class_=re.compile(r"JobCard_jobDescriptionSnippet|jobDesc"))
            if desc_el:
                return desc_el.get_text(strip=True)
            return "See full job description on Glassdoor"

        elif parameter == JobField.LOCATION:
            # Glassdoor uses JobCard_location__* class
            loc_el = soup.find(class_=re.compile(r"JobCard_location"))
            if not loc_el:
                loc_el = soup.find(attrs={"data-test": "emp-location"})
            if not loc_el:
                loc_el = soup.find(class_=re.compile(r"location|Location"))
            return loc_el.get_text(strip=True) if loc_el else ""

        elif parameter == JobField.TAGS:
            tags = []
            # Look for badges, benefits, etc.
            badge_els = soup.find_all(class_=re.compile(r"badge|tag|benefit|perk"))
            for badge in badge_els:
                text = badge.get_text(strip=True)
                if text and len(text) < 100:
                    tags.append(text)
            return tags[:10]

        elif parameter == JobField.WAGE:
            # Look for salary info
            salary_el = soup.find(attrs={"data-test": "detailSalary"})
            if not salary_el:
                salary_el = soup.find(class_=re.compile(r"salary|Salary|compensation"))
            if salary_el:
                return salary_el.get_text(strip=True)
            return ""

        elif parameter == JobField.POST_DATE:
            # Look for posted date
            date_el = soup.find(attrs={"data-test": "job-age"})
            if not date_el:
                date_el = soup.find(class_=re.compile(r"job-age|listingAge|posted"))
            if date_el:
                rel_time = date_el.get_text(strip=True)
                if rel_time:
                    return calc_post_date_from_relative_str(rel_time)
            return None

        elif parameter == JobField.KEY_ID:
            return self._extract_job_id_from_soup(soup)

        else:
            raise NotImplementedError(f"Cannot get {parameter.name}")

    def set(self, parameter: JobField, job: Job, soup: BeautifulSoup) -> None:
        """Set a single job attribute from a soup object by JobField."""
        if parameter == JobField.URL:
            link = soup.find("a", href=re.compile(r"/job-listing/|/partner/jobListing"))
            if link:
                href = link.get("href", "")
                if isinstance(href, str):
                    if href.startswith("/"):
                        job.url = f"https://www.glassdoor.com{href}"
                    else:
                        job.url = href
                else:
                    job.url = f"https://www.glassdoor.com/Job/jobs.htm?jobListingId={job.key_id or ''}"
            else:
                job.url = f"https://www.glassdoor.com/Job/jobs.htm?jobListingId={job.key_id or ''}"

        elif parameter == JobField.REMOTENESS:
            text = soup.get_text().lower()
            if "remote" in text:
                if "hybrid" in text:
                    job.remoteness = Remoteness.PARTIALLY_REMOTE
                else:
                    job.remoteness = Remoteness.FULLY_REMOTE
            elif "on-site" in text or "onsite" in text:
                job.remoteness = Remoteness.IN_PERSON
            else:
                job.remoteness = Remoteness.UNKNOWN

        elif parameter == JobField.RAW:
            pass

        else:
            raise NotImplementedError(f"Cannot set {parameter.name}")


class GlassdoorScraperUSAEng(BaseGlassdoorScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.glassdoor.com (USA)"""


class GlassdoorScraperCANEng(BaseGlassdoorScraper, BaseCANEngScraper):
    """Scrapes jobs from www.glassdoor.ca (Canada)"""

    def _get_search_url(self) -> str:
        """Get the Glassdoor Canada jobs search URL."""
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        location = f"{city}, {province_or_state}".strip(", ")

        # Glassdoor Canada uses .ca domain
        base_url = "https://www.glassdoor.ca/Job/jobs.htm"
        params = [
            f"sc.keyword={self.query.replace(' ', '%20')}",
            f"locT=C",
            f"locKeyword={location.replace(' ', '%20').replace(',', '%2C')}",
        ]

        radius = self.config.search_config.radius
        if radius:
            params.append(f"radius={radius}")

        return f"{base_url}?{'&'.join(params)}"


class GlassdoorScraperUKEng(BaseGlassdoorScraper, BaseUKEngScraper):
    """Scrapes jobs from www.glassdoor.co.uk (UK)"""

    def _get_search_url(self) -> str:
        """Get the Glassdoor UK jobs search URL."""
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        location = f"{city}, {province_or_state}".strip(", ")

        # Glassdoor UK uses .co.uk domain
        base_url = "https://www.glassdoor.co.uk/Job/jobs.htm"
        params = [
            f"sc.keyword={self.query.replace(' ', '%20')}",
            f"locT=C",
            f"locKeyword={location.replace(' ', '%20').replace(',', '%2C')}",
        ]

        radius = self.config.search_config.radius
        if radius:
            params.append(f"radius={radius}")

        return f"{base_url}?{'&'.join(params)}"
