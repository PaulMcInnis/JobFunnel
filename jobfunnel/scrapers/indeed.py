"""Scraper designed to get jobs from www.indeed.com / www.indeed.ca
"""
from abc import ABC, abstractmethod
import datetime
from typing import Dict, List
from requests import Session

from jobfunnel.job import Job
from jobfunnel.localization import Locale, get_domain_from_locale
from jobfunnel.search_terms import SearchTerms
from jobfunnel.scrapers.base import Scraper


class BaseIndeedScraper(Scraper):
    """Scrapes jobs from www.indeed.X
    """
    def __init__(self, session: Session, search_terms: SearchTerms) -> None:
        """Init that contains indeed specific stuff
        """
        self.max_results_per_page = 50
        self.search_terms = search_terms
        self.query = '+'.join(self.search_terms.keywords)

    def scrape(self) -> List[Job]:
        """Scrapes raw data from a job source into a list of Job objects

        Returns:
            List[Job]: list of jobs scraped from the job source
        """
        return [  # FIXME: testing...
            Job(
                title="Beef Collector",
                company="Orwell Farms",
                location="Middle Earth, Canada",
                scrape_date=datetime.datetime.now(),
                description="Collect beef, earn sand dollars",
                key_id="d3adb33f",
                url="www.indeed.ca/test-job1",
                locale=Locale.CANADA_ENGLISH,
                post_date=datetime.datetime.now(),
                raw="HTML:someran/domdatahereHeept;atag:s2311",
                tags=['beef', 'collector', 'apply', 'now'],
            ),
            Job(
                title="Chickun Inhibitor",
                company="Roswell Park",
                location="Middle South, Canada",
                scrape_date=datetime.datetime.now(),
                description="Collect Chickun, earn sand dollars",
                key_id="d4adb44f",
                url="www.indeed.ca/test-job2",
                locale=Locale.CANADA_ENGLISH,
                post_date=datetime.datetime.now(),
                raw="HTML:somera3n/domdatahereHeept;atag:s231131",
                tags=['chickun', 'collector', 'apply', 'now'],
            )
        ]

    def filter_jobs(self, jobs: List[Job]) -> List[Job]:
        """Descriminate each Job in jobs using filters

        TODO: use self.filters: List[Filter]

        Args:
            jobs (List[job]): input jobs

        Returns:
            List[Job]: output jobs
        """
        return jobs # FIXME: testing...


class IndeedScraperCA(BaseIndeedScraper):
    """Scrapes jobs from www.indeed.ca
    """
    @property
    def locale(self) -> Locale:
        return Locale.CANADA_ENGLISH

    @property
    def headers(self) -> Dict[str, str]:
        """Session header for Indeed
        """
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',  # FIXME
            'referer': 'https://www.indeed.{0}/'.format(
                get_domain_from_locale(self.locale)),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }


class IndeedScraperUSA(BaseIndeedScraper):
    """Scrapes jobs from www.indeed.com
    """
    @property
    def locale(self) -> Locale:
        return Locale.USA_ENGLISH

    @property
    def headers(self) -> Dict[str, str]:
        """Session header for Indeed
        """
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',   # FIXME
            'referer': 'https://www.indeed.{0}/'.format(
                get_domain_from_locale(self.locale)),
            'upgrade-insecure-requests': '1',
            'user-agent': self.user_agent,
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
