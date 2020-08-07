"""Lookup tables where we can map scrapers to locales, etc
"""
from jobfunnel.backend.scrapers import (
    BaseScraper, IndeedScraperCAEng, IndeedScraperUSAEng, GlassDoorStaticCAEng,
    GlassDoorStaticUSAEng,
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
    Provider.GLASSDOOR: {
        Locale.CANADA_ENGLISH: GlassDoorStaticCAEng,
        Locale.CANADA_ENGLISH: GlassDoorStaticUSAEng,
    },
    # 'monster': MonsterScraperCAEng,  FIXME
    #'MONSTER_CANADA_ENG': MonsterScraperCAEng,
}  # type:


