"""Object to contain job query metadata
"""

from typing import List, Optional

from jobfunnel.config import BaseConfig
from jobfunnel.resources import Locale, Provider, Remoteness
from jobfunnel.resources.defaults import (
    DEFAULT_DOMAIN_FROM_LOCALE,
    DEFAULT_MAX_LISTING_DAYS,
    DEFAULT_SEARCH_RADIUS,
)


class SearchConfig(BaseConfig):
    """Config object containing our desired job search information including
    the Locale of the searcher, the region to search and what job providers to
    search with.
    """

    def __init__(
        self,
        keywords: List[str],
        province_or_state: Optional[str],
        locale: Locale,
        providers: List[Provider],
        city: Optional[str] = None,
        distance_radius: Optional[int] = None,
        return_similar_results: bool = False,
        max_listing_days: Optional[int] = None,
        blocked_company_names: Optional[List[str]] = None,
        domain: Optional[str] = None,
        remoteness: Optional[Remoteness] = Remoteness.ANY,
    ):
        """Search config for all job sources

        Args:
            keywords (List[str]): list of search keywords
            province_or_state (str): province or state.
            locale(Locale): the searcher's Locale, defines the job website
                domain and the scrapers we will use to scrape it.
            city (Optional[str], optional): city. Defaults to None.
            distance_radius (Optional[int], optional): km/m radius. Defaults to
                DEFAULT_SEARCH_RADIUS.
            return_similar_results (Optional[bool], optional): return similar.
                results (indeed), Defaults to False.
            max_listing_days (Optional[int], optional): oldest listing to show.
                Defaults to DEFAULT_MAX_LISTING_DAYS.
            blocked_company_names (Optional[List[str]]): list of names of
                companies that we never want to see in our results.
            domain (Optional[str], optional): domain string to use for search
                querying. If not passed, will set based on locale. (i.e. 'ca')
            remoteness: The level of work-remoteness desired. Defaults to any.
        """
        super().__init__()
        self.province_or_state = province_or_state
        self.city = city.lower() if city else None
        self.radius = distance_radius or DEFAULT_SEARCH_RADIUS
        self.locale = locale
        self.providers = providers
        self.keywords = keywords
        self.return_similar_results = return_similar_results  # Indeed.X thing
        self.max_listing_days = max_listing_days or DEFAULT_MAX_LISTING_DAYS
        self.blocked_company_names = blocked_company_names
        self.remoteness = remoteness

        # Try to infer the domain string based on the locale.
        if not domain:
            if self.locale not in DEFAULT_DOMAIN_FROM_LOCALE:
                raise ValueError(f"Unknown domain for locale: {self.locale}")
            self.domain = DEFAULT_DOMAIN_FROM_LOCALE[self.locale]
        else:
            self.domain = domain

    @property
    def query_string(self) -> str:
        """User-readable version of the keywords we are searching with for CSV"""
        return " ".join(self.keywords)

    def validate(self):
        """We need to have the right information set, not mixing stuff"""
        assert self.province_or_state is not None, "Province/State not set"
        assert self.city, "City not set"
        assert self.locale, "Locale not set"
        assert self.providers and len(self.providers) >= 1, "Providers not set"
        assert self.keywords and len(self.keywords) >= 1, "Keywords not set"
        assert self.max_listing_days >= 1, "Cannot set max posting days < 1"
        assert self.domain, "Domain not set"
        assert self.remoteness != Remoteness.UNKNOWN, "Remoteness is UNKNOWN!"
