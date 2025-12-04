"""Lookup tables where we can map scrapers to locales, etc

NOTE: if you implement a scraper you must add it here
TODO: there must be a better way to do this by using class attrib of Provider
"""

from jobfunnel.backend.scrapers.indeed import (
    IndeedScraperCANEng,
    IndeedScraperDEGer,
    IndeedScraperFRFre,
    IndeedScraperUKEng,
    IndeedScraperUSAEng,
)
from jobfunnel.resources import Locale, Provider

SCRAPER_FROM_LOCALE = {
    # search terms which one to use
    Provider.INDEED: {
        Locale.CANADA_ENGLISH: IndeedScraperCANEng,
        Locale.USA_ENGLISH: IndeedScraperUSAEng,
        Locale.UK_ENGLISH: IndeedScraperUKEng,
        Locale.FRANCE_FRENCH: IndeedScraperFRFre,
        Locale.GERMANY_GERMAN: IndeedScraperDEGer,
    },
}
