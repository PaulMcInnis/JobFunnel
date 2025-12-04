"""Scraper designed to get jobs from www.linkedin.com using Playwright browser automation.

LinkedIn requires authentication. If not logged in, the scraper will open a browser
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

MAX_RESULTS_PER_LINKEDIN_PAGE = 25

REMOTENESS_FILTER_MAP = {
    Remoteness.FULLY_REMOTE: "2",  # f_WT=2 for remote
    Remoteness.PARTIALLY_REMOTE: "3",  # f_WT=3 for hybrid
    Remoteness.IN_PERSON: "1",  # f_WT=1 for on-site
}


class BaseLinkedInScraper(BaseScraper):
    """Scrapes jobs from www.linkedin.com using Playwright for browser automation.

    Uses a persistent browser context to maintain login state between runs.
    If not logged in, will prompt user to log in manually in the browser window.
    """

    def __init__(self, session: Session, config: "JobFunnelConfigManager", job_filter: JobFilter) -> None:
        """Init that contains LinkedIn specific stuff"""
        super().__init__(session, config, job_filter)
        self.max_results_per_page = MAX_RESULTS_PER_LINKEDIN_PAGE
        self.query = " ".join(self.config.search_config.keywords)
        self._browser: Optional[Browser] = None
        self._playwright = None

        # Set up persistent browser data directory for maintaining login
        self._user_data_dir = Path(self.config.cache_folder) / "browser_data_linkedin"
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
        """Get the LinkedIn jobs search URL."""
        city = self.config.search_config.city or ""
        province_or_state = self.config.search_config.province_or_state or ""
        location = f"{city}, {province_or_state}".strip(", ")

        base_url = "https://www.linkedin.com/jobs/search/"
        params = [
            f"keywords={self.query.replace(' ', '%20')}",
            f"location={location.replace(' ', '%20').replace(',', '%2C')}",
        ]

        # Add remoteness filter if specified
        remoteness = self.config.search_config.remoteness
        if remoteness and remoteness in REMOTENESS_FILTER_MAP:
            params.append(f"f_WT={REMOTENESS_FILTER_MAP[remoteness]}")

        # Add distance filter (LinkedIn uses miles)
        radius = self.config.search_config.radius
        if radius:
            params.append(f"distance={radius}")

        return f"{base_url}?{'&'.join(params)}"

    def _check_login_status(self, page: Page) -> bool:
        """Check if we're logged in to LinkedIn."""
        try:
            # Check URL - if we're on login/authwall page, not logged in
            if "/login" in page.url or "/authwall" in page.url or "/checkpoint" in page.url:
                return False

            # Check for elements that indicate we're logged in
            # The global nav or scaffold layout appears when logged in
            nav = page.query_selector('nav[class*="global-nav"]')
            if nav:
                return True

            scaffold = page.query_selector('div[class*="scaffold"]')
            if scaffold:
                return True

            # Check for sign-in button (means NOT logged in)
            login_button = page.query_selector('a[href*="login"], button[class*="sign-in"]')
            if login_button:
                return False

            return False
        except Exception:
            return False

    def _wait_for_manual_login(self, page: Page, context: BrowserContext) -> bool:
        """Wait for user to manually log in to LinkedIn.

        Returns True if login successful, False if timed out or failed.
        """
        self.logger.info("")
        self.logger.info("=" * 60)
        self.logger.info("  LinkedIn Login Required")
        self.logger.info("=" * 60)
        self.logger.info("")
        self.logger.info("Please log in to LinkedIn in the browser window.")
        self.logger.info("Complete any 2FA/CAPTCHA if required.")
        self.logger.info("The scraper will continue automatically once logged in.")
        self.logger.info("")
        self.logger.info("Waiting for login (timeout: 5 minutes)...")

        # Navigate to login page
        page.goto("https://www.linkedin.com/login", timeout=60000)

        # Wait for login to complete (check every 2 seconds for 5 minutes)
        max_wait_seconds = 300
        check_interval = 2
        elapsed = 0

        while elapsed < max_wait_seconds:
            page.wait_for_timeout(check_interval * 1000)
            elapsed += check_interval

            # Check if we're now logged in (redirected away from login page)
            if self._check_login_status(page):
                self.logger.info("Login successful!")
                return True

            # Also check if we're on the feed or jobs page
            if "/feed" in page.url or "/jobs" in page.url:
                self.logger.info("Login successful!")
                return True

        self.logger.error("Login timed out after 5 minutes.")
        return False

    def get_job_soups_from_search_result_listings(self) -> List[BeautifulSoup]:
        """Scrapes raw data from LinkedIn using Playwright browser automation.

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
                # Navigate to LinkedIn jobs search
                search_url = self._get_search_url()
                self.logger.info("Navigating to LinkedIn jobs: %s", search_url)
                page.goto(search_url, timeout=60000)
                page.wait_for_timeout(3000)

                # Check if we're logged in, prompt for login if not
                if not self._check_login_status(page):
                    self.logger.info("Not logged in to LinkedIn, prompting for login...")
                    if not self._wait_for_manual_login(page, context):
                        raise ValueError("LinkedIn login required but not completed.")

                    # Navigate back to search after login
                    page.goto(search_url, timeout=60000)
                    page.wait_for_timeout(3000)

                # Wait for job listings to load
                try:
                    page.wait_for_selector(
                        'div[class*="job-card"], li[class*="jobs-search-results"]',
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
                    # LinkedIn uses pagination with page numbers
                    next_btn = page.query_selector(f'button[aria-label="Page {page_num + 1}"]')
                    if not next_btn:
                        # Try aria-label pattern for Next
                        next_btn = page.query_selector('button[aria-label*="next" i]')
                    if not next_btn:
                        # Try looking for next page link
                        next_btn = page.query_selector("li[data-test-pagination-page-btn] + li button")

                    if next_btn:
                        self.logger.info("Clicking to go to page %d", page_num + 1)
                        next_btn.click()
                        page.wait_for_timeout(3000)
                        self._extract_jobs_from_page(page, job_soup_list)
                    else:
                        # Try scrolling to load more jobs (LinkedIn infinite scroll)
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

            # Look for job count text like "X results" or "X jobs"
            match = re.search(r"([\d,]+)\s*(results?|jobs?)", page_content, re.IGNORECASE)
            if match:
                total_jobs = int(match.group(1).replace(",", ""))
                return min(ceil(total_jobs / MAX_RESULTS_PER_LINKEDIN_PAGE), 5)

            # Look for pagination info
            pagination = page.query_selector('div[class*="pagination"]')
            if pagination:
                page_buttons = pagination.query_selector_all("button")
                if page_buttons:
                    return min(len(page_buttons), 5)

            self.logger.warning("Could not determine page count, defaulting to 1")
            return 1

        except Exception as e:
            self.logger.warning("Error getting page count: %s", e)
            return 1

    def _extract_jobs_from_page(self, page: Page, job_soup_list: List[BeautifulSoup]) -> None:
        """Extract job data from a loaded LinkedIn search results page."""
        page_content = page.content()
        if self.config.debug_scrape:
            self.dump_debug_html(page_content, f"page_{len(job_soup_list)}")
        soup = BeautifulSoup(page_content, self.config.bs4_parser)

        # LinkedIn job cards - try multiple selectors
        job_cards = soup.find_all("div", class_=re.compile(r"job-card-container"))
        if not job_cards:
            job_cards = soup.find_all("li", class_=re.compile(r"jobs-search-results__list-item"))
        if not job_cards:
            job_cards = soup.find_all("div", {"data-job-id": True})
        if not job_cards:
            # Try finding cards by the job link pattern
            job_links = soup.find_all("a", href=re.compile(r"/jobs/view/\d+"))
            job_cards = [link.find_parent("div") or link.find_parent("li") for link in job_links]
            job_cards = [c for c in job_cards if c]  # Filter None

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
        # Try data-job-id attribute
        job_id_el = soup.find(attrs={"data-job-id": True})
        if job_id_el:
            job_id = job_id_el.get("data-job-id")
            if job_id:
                return str(job_id)

        # Try extracting from job link
        link = soup.find("a", href=re.compile(r"/jobs/view/(\d+)"))
        if link:
            href = link.get("href", "")
            if isinstance(href, str):
                match = re.search(r"/jobs/view/(\d+)", href)
                if match:
                    return match.group(1)

        # Try data-occludable-job-id
        occludable = soup.find(attrs={"data-occludable-job-id": True})
        if occludable:
            return str(occludable.get("data-occludable-job-id", ""))

        return ""

    def get(self, parameter: JobField, soup: BeautifulSoup) -> Any:
        """Get a single job attribute from a soup object."""
        if parameter == JobField.TITLE:
            # LinkedIn uses artdeco-entity-lockup__title for job titles
            title_el = soup.find(class_=re.compile(r"artdeco-entity-lockup__title"))
            if title_el:
                # Get text from the link or strong inside
                link = title_el.find("a")
                if link:
                    return link.get_text(strip=True)
                strong = title_el.find("strong")
                if strong:
                    return strong.get_text(strip=True)
                return title_el.get_text(strip=True)
            # Fallback selectors
            title_el = soup.find(class_=re.compile(r"job-card-list__title|base-search-card__title"))
            if not title_el:
                title_el = soup.find("strong")
            return title_el.get_text(strip=True) if title_el else ""

        elif parameter == JobField.COMPANY:
            # LinkedIn uses artdeco-entity-lockup__subtitle for company name
            company_el = soup.find(class_=re.compile(r"artdeco-entity-lockup__subtitle"))
            if company_el:
                return company_el.get_text(strip=True)
            # Fallback selectors
            company_el = soup.find(class_=re.compile(r"job-card-container__company-name|base-search-card__subtitle"))
            return company_el.get_text(strip=True) if company_el else ""

        elif parameter == JobField.DESCRIPTION:
            # LinkedIn search results have limited description
            desc_el = soup.find(class_=re.compile(r"job-card-list__insight|job-card__snippet"))
            if desc_el:
                return desc_el.get_text(strip=True)
            return "See full job description on LinkedIn"

        elif parameter == JobField.LOCATION:
            # LinkedIn uses artdeco-entity-lockup__caption for location metadata
            caption_el = soup.find(class_=re.compile(r"artdeco-entity-lockup__caption"))
            if caption_el:
                # Location is usually the first li in the metadata wrapper
                li = caption_el.find("li")
                if li:
                    return li.get_text(strip=True)
                return caption_el.get_text(strip=True)
            # Fallback selectors
            loc_el = soup.find(class_=re.compile(r"job-card-container__metadata-item|job-search-card__location"))
            return loc_el.get_text(strip=True) if loc_el else ""

        elif parameter == JobField.TAGS:
            tags = []
            # Look for benefits, requirements, badges
            badge_els = soup.find_all(class_=re.compile(r"badge|benefit|insight"))
            for badge in badge_els:
                text = badge.get_text(strip=True)
                if text and len(text) < 100:  # Avoid grabbing large text blocks
                    tags.append(text)
            return tags[:10]  # Limit tags

        elif parameter == JobField.WAGE:
            # Look for salary info
            salary_el = soup.find(class_=re.compile(r"salary|compensation|pay"))
            if salary_el:
                return salary_el.get_text(strip=True)
            # Check in metadata items
            metadata = soup.find_all(class_=re.compile(r"metadata-item"))
            for item in metadata:
                text = item.get_text(strip=True)
                if "$" in text or "salary" in text.lower():
                    return text
            return ""

        elif parameter == JobField.POST_DATE:
            # Look for posted date
            date_el = soup.find(class_=re.compile(r"job-card-container__listed-time|listed-time"))
            if not date_el:
                date_el = soup.find("time")
            if date_el:
                # Try datetime attribute first
                datetime_attr = date_el.get("datetime")
                if datetime_attr:
                    return calc_post_date_from_relative_str(str(datetime_attr))
                # Fallback to text
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
            link = soup.find("a", href=re.compile(r"/jobs/view/"))
            if link:
                href = link.get("href", "")
                if isinstance(href, str):
                    if href.startswith("/"):
                        job.url = f"https://www.linkedin.com{href}"
                    else:
                        job.url = href
                else:
                    job.url = f"https://www.linkedin.com/jobs/view/{job.key_id or ''}"
            else:
                job.url = f"https://www.linkedin.com/jobs/view/{job.key_id or ''}"

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


class LinkedInScraperUSAEng(BaseLinkedInScraper, BaseUSAEngScraper):
    """Scrapes jobs from www.linkedin.com (USA)"""


class LinkedInScraperCANEng(BaseLinkedInScraper, BaseCANEngScraper):
    """Scrapes jobs from www.linkedin.com (Canada)"""


class LinkedInScraperUKEng(BaseLinkedInScraper, BaseUKEngScraper):
    """Scrapes jobs from www.linkedin.com (UK)"""
