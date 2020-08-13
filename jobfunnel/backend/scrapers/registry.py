"""Lookup tables where we can map scrapers to locales, etc

NOTE: if you implement a scraper you must add it here or JobFunnel cannot
find it.
TODO: way to make this unnecessary? maybe import & map based on name?
"""
from jobfunnel.resources import Locale, Provider

from jobfunnel.backend.scrapers.indeed import (
    IndeedScraperCANEng, IndeedScraperUSAEng,
)
from jobfunnel.backend.scrapers.monster import (
    MonsterScraperCANEng, MonsterScraperUSAEng,
)
from jobfunnel.backend.scrapers.glassdoor.driven import (
    DrivenGlassDoorScraperUSAEng, DrivenGlassDoorScraperCANEng,
)
from jobfunnel.backend.scrapers.glassdoor.static import (
    StaticGlassDoorScraperCANEng, StaticGlassDoorScraperUSAEng,
)



# NOTE: if you add a scraper you need to add it here
# TODO: there must be a better way to do this by using class attrib of Provider
SCRAPER_FROM_LOCALE = {
    # search terms which one to use
    Provider.INDEED: {
        Locale.CANADA_ENGLISH: IndeedScraperCANEng,
        Locale.USA_ENGLISH: IndeedScraperUSAEng,
    },
    Provider.GLASSDOOR: {  # FIXME
        Locale.CANADA_ENGLISH: StaticGlassDoorScraperCANEng,
        Locale.USA_ENGLISH: StaticGlassDoorScraperUSAEng,
    },
    Provider.MONSTER: {
        Locale.CANADA_ENGLISH: MonsterScraperCANEng,
        Locale.USA_ENGLISH: MonsterScraperUSAEng,
    },
}


# Any of the web-driven scrapers will be chosen if we set --web-driven
# TODO: have defaults for these instead.
DRIVEN_SCRAPER_FROM_LOCALE = {
    Provider.GLASSDOOR: {
        Locale.CANADA_ENGLISH: DrivenGlassDoorScraperCANEng,
        Locale.USA_ENGLISH: DrivenGlassDoorScraperUSAEng,
    },
}