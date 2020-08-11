from jobfunnel.backend.scrapers.base import (
    BaseScraper, BaseCANEngScraper, BaseUSAEngScraper,
)
from jobfunnel.backend.scrapers.indeed import (
    IndeedScraperCAEng, IndeedScraperUSAEng,
)
from jobfunnel.backend.scrapers.glassdoor.static import (
    GlassDoorStaticCAEng, GlassDoorStaticUSAEng,
)
from jobfunnel.backend.scrapers.monster import (
    MonsterScraperCAEng, MonsterScraperUSAEng,
)
from jobfunnel.backend.scrapers.registry import SCRAPER_FROM_LOCALE
