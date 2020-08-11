"""Lookup tables where we can map scrapers to locales, etc

NOTE: if you implement a scraper you must add it here or JobFunnel cannot
find it.
TODO: way to make this unnecessary? maybe import & map based on name?
"""
from jobfunnel.backend.scrapers import (
    BaseScraper, IndeedScraperCAEng, IndeedScraperUSAEng, GlassDoorStaticCAEng,
    GlassDoorStaticUSAEng, MonsterScraperCAEng, MonsterScraperUSAEng,
)
from jobfunnel.resources import Locale, Provider


# NOTE: if you add a scraper you need to add it here
# TODO: there must be a better way to do this by using class attrib of Provider
SCRAPER_FROM_LOCALE = {
    # search terms which one to use
    Provider.INDEED: {
        Locale.CANADA_ENGLISH: IndeedScraperCAEng,
        Locale.USA_ENGLISH: IndeedScraperUSAEng,
    },
    # Provider.GLASSDOOR: {  # FIXME
    #     Locale.CANADA_ENGLISH: GlassDoorStaticCAEng,
    #     Locale.CANADA_ENGLISH: GlassDoorStaticUSAEng,
    # },
    Provider.MONSTER: {
        Locale.CANADA_ENGLISH: MonsterScraperCAEng,
        Locale.USA_ENGLISH: MonsterScraperUSAEng,
    },
}
