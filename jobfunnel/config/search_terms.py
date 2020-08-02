"""Object to contain job query metadata
"""
from typing import List, Optional
from jobfunnel.backend.localization import Locale
from jobfunnel.config import BaseConfig


DEFAULT_SEARCH_RADIUS_KM = 25
DEFAULT_MAX_LISTING_DAYS = 10


class SearchTerms(BaseConfig):
    """Config object to contain region of interest for a Locale

    NOTE: ideally we'd have one of these per-locale, per-website, but then
    the config would be a nightmare, so we'll just put everything in here
    for now
    FIXME: need a better soln since this is required to be too flexible...
    perhaps something at the Scraper level?
    TODO: move into serach terms...
    """

    def __init__(self,
                 keywords: List[str],
                 province: Optional[str] = None,
                 state: Optional[str] = None,
                 city: Optional[str] = None,
                 distance_radius_km: Optional[int] = DEFAULT_SEARCH_RADIUS_KM,
                 return_similar_results: Optional[bool] = False,
                 max_listing_days: Optional[int] = DEFAULT_MAX_LISTING_DAYS):
        """init TODO: document"""
        self.province = province
        self.state = state
        self.city = city
        self.radius = distance_radius_km
        self.keywords = keywords
        self.return_similar_results = return_similar_results  # indeed thing
        self.max_listing_days = max_listing_days

    def is_valid(self, locale: Locale) -> bool:
        """we need to have the right information set, not mixing stuff
        TODO: eval is_valid based on the scraper as well?
        """
        if not self.keywords:
            return False
        if locale in [Locale.CANADA_ENGLISH, Locale.CANADA_FRENCH]:
            return self.province and not self.state
        elif locale == Locale.USA_ENGLISH:
            return not self.province and self.state
