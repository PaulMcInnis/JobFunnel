"""Lookup tables where we can map scrapers to locales, etc

NOTE: if you implement a scraper you must add it here
TODO: there must be a better way to do this by using class attrib of Provider
"""
from jobfunnel.resources import Locale, Provider

from jobfunnel.backend.scrapers.indeed import (
    IndeedScraperCANEng, IndeedScraperUSAEng,
    IndeedScraperUKEng,
)
from jobfunnel.backend.scrapers.monster import (
    MonsterScraperCANEng, MonsterScraperUSAEng,
    MonsterScraperUKEng,
)
from jobfunnel.backend.scrapers.glassdoor import (
    GlassDoorScraperCANEng, GlassDoorScraperUSAEng,
    GlassDoorScraperUKEng
)

SCRAPER_FROM_LOCALE = {
    # search terms which one to use
    Provider.INDEED: {
        Locale.CANADA_ENGLISH: IndeedScraperCANEng,
        Locale.USA_ENGLISH: IndeedScraperUSAEng,
        Locale.UK_ENGLISH: IndeedScraperUKEng,
    },
    Provider.GLASSDOOR: {
        Locale.CANADA_ENGLISH: GlassDoorScraperCANEng,
        Locale.USA_ENGLISH: GlassDoorScraperUSAEng,
        Locale.UK_ENGLISH: GlassDoorScraperUKEng,
    },
    Provider.MONSTER: {
        Locale.CANADA_ENGLISH: MonsterScraperCANEng,
        Locale.USA_ENGLISH: MonsterScraperUSAEng,
        Locale.UK_ENGLISH: MonsterScraperUKEng,
    },
}
