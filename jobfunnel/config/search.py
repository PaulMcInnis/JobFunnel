"""Object to contain job query metadata
"""
from typing import List, Optional
from jobfunnel.config import BaseConfig
from jobfunnel.resources import (
    Locale, DEFAULT_SEARCH_RADIUS_KM, DEFAULT_MAX_LISTING_DAYS
)


class SearchConfig(BaseConfig):
    """Config object to contain region of interest for a Locale

    FIXME: ideally we'd have one of these per-locale, per-website, but then
    the config would be a nightmare, so we'll just put everything in here
    for now
    """

    def __init__(self,
                 keywords: List[str],
                 province_or_state: Optional[str] = None,
                 # state: Optional[str] = None,  TODO: impl. per-locale ?
                 city: Optional[str] = None,
                 distance_radius_km: Optional[int] = None,
                 return_similar_results: Optional[bool] = False,
                 max_listing_days: Optional[int] = None,
                 blocked_company_names: Optional[List[str]] = None):
        """Search config for all job sources

        Args:
            keywords (List[str]): list of search keywords
            province_or_state (Optional[str], optional): province or state.
                Defaults to None.
            city (Optional[str], optional): city. Defaults to None.
            distance_radius_km (Optional[int], optional): km radius. Defaults to
                DEFAULT_SEARCH_RADIUS_KM.
            return_similar_results (Optional[bool], optional): return similar.
                results (indeed), Defaults to False.
            max_listing_days (Optional[int], optional): oldest listing to show.
                Defaults to DEFAULT_MAX_LISTING_DAYS.
            blocked_company_names (Optional[List[str]]): list of names of
                companies that we never want to see in our results.
        """
        self.province = province_or_state
        self.state = province_or_state
        self.city = city.lower()
        self.radius = distance_radius_km or DEFAULT_SEARCH_RADIUS_KM
        self.keywords = keywords
        self.return_similar_results = return_similar_results  # indeed thing
        self.max_listing_days = max_listing_days or DEFAULT_MAX_LISTING_DAYS
        self.blocked_company_names = blocked_company_names

    def validate(self):
        """We need to have the right information set, not mixing stuff
        FIXME: impl.
        """
        pass
