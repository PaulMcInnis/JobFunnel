"""Lookup tables where we can map scrapers to locales, etc

NOTE: if you implement a scraper you must add it here
TODO: there must be a better way to do this by using class attrib of Provider
"""
from jobfunnel.resources import Locale, Provider

from jobfunnel.backend.scrapers.indeed import (
    IndeedScraperCANEng, IndeedScraperUSAEng,
)
from jobfunnel.backend.scrapers.monster import (
    MonsterScraperCANEng, MonsterScraperUSAEng,
)
from jobfunnel.backend.scrapers.glassdoor import (
    GlassDoorScraperCANEng, GlassDoorScraperUSAEng,
)

SCRAPER_FROM_LOCALE = {
    # search terms which one to use
    Provider.INDEED: {
        Locale.CANADA_ENGLISH: IndeedScraperCANEng,
        Locale.USA_ENGLISH: IndeedScraperUSAEng,
    },
    Provider.GLASSDOOR: {
        Locale.CANADA_ENGLISH: GlassDoorScraperCANEng,
        Locale.USA_ENGLISH: GlassDoorScraperUSAEng,
    },
    Provider.MONSTER: {
        Locale.CANADA_ENGLISH: MonsterScraperCANEng,
        Locale.USA_ENGLISH: MonsterScraperUSAEng,
    },
}
