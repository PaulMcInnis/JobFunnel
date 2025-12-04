"""Lookup tables where we can map scrapers to locales, etc

NOTE: if you implement a scraper you must add it here
TODO: there must be a better way to do this by using class attrib of Provider
"""

from typing import TYPE_CHECKING, Dict, Type

from jobfunnel.backend.scrapers.glassdoor import (
    GlassdoorScraperCANEng,
    GlassdoorScraperUKEng,
    GlassdoorScraperUSAEng,
)
from jobfunnel.backend.scrapers.indeed import (
    IndeedScraperCANEng,
    IndeedScraperDEGer,
    IndeedScraperFRFre,
    IndeedScraperUKEng,
    IndeedScraperUSAEng,
)
from jobfunnel.backend.scrapers.linkedin import (
    LinkedInScraperCANEng,
    LinkedInScraperUKEng,
    LinkedInScraperUSAEng,
)
from jobfunnel.backend.scrapers.simplyhired import (
    SimplyHiredScraperCANEng,
    SimplyHiredScraperUSAEng,
)
from jobfunnel.resources import Locale, Provider

if TYPE_CHECKING:
    from jobfunnel.backend.scrapers.base import BaseScraper

SCRAPER_FROM_LOCALE: Dict[Provider, Dict[Locale, Type["BaseScraper"]]] = {
    Provider.INDEED: {
        Locale.CANADA_ENGLISH: IndeedScraperCANEng,
        Locale.USA_ENGLISH: IndeedScraperUSAEng,
        Locale.UK_ENGLISH: IndeedScraperUKEng,
        Locale.FRANCE_FRENCH: IndeedScraperFRFre,
        Locale.GERMANY_GERMAN: IndeedScraperDEGer,
    },
    Provider.SIMPLYHIRED: {
        Locale.CANADA_ENGLISH: SimplyHiredScraperCANEng,
        Locale.USA_ENGLISH: SimplyHiredScraperUSAEng,
    },
    Provider.LINKEDIN: {
        Locale.CANADA_ENGLISH: LinkedInScraperCANEng,
        Locale.USA_ENGLISH: LinkedInScraperUSAEng,
        Locale.UK_ENGLISH: LinkedInScraperUKEng,
    },
    Provider.GLASSDOOR: {
        Locale.CANADA_ENGLISH: GlassdoorScraperCANEng,
        Locale.USA_ENGLISH: GlassdoorScraperUSAEng,
        Locale.UK_ENGLISH: GlassdoorScraperUKEng,
    },
}
