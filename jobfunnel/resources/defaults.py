"""Default arguments for both JobFunnelConfigManager and CLI arguments.
NOTE: Not all defaults here are used, as we rely on YAML for demo and not kwargs
"""
import os
from pathlib import Path
from jobfunnel.resources.enums import Locale, DelayAlgorithm, Provider

USER_HOME_DIRECTORY = os.path.abspath(str(Path.home()))

DEFAULT_LOG_LEVEL_NAME = 'INFO'
DEFAULT_LOCALE = Locale.CANADA_ENGLISH
DEFAULT_CITY = 'Waterloo'
DEFAULT_PROVINCE = 'ON'
DEFAULT_SEARCH_KEYWORDS = ['Python']
DEFAULT_COMPANY_BLOCK_LIST = []
DEFAULT_OUTPUT_DIRECTORY = os.path.join(
    USER_HOME_DIRECTORY, 'job_search_results'
)
DEFAULT_CACHE_DIRECTORY = os.path.join(DEFAULT_OUTPUT_DIRECTORY, '.cache')
DEFAULT_BLOCK_LIST_FILE = os.path.join(DEFAULT_CACHE_DIRECTORY, 'block.json')
DEFAULT_DUPLICATES_FILE = os.path.join(
    DEFAULT_CACHE_DIRECTORY, 'duplicates.json'
)
DEFAULT_LOG_FILE = os.path.join(DEFAULT_OUTPUT_DIRECTORY, 'log.log')
DEFAULT_MASTER_CSV_FILE = os.path.join(DEFAULT_OUTPUT_DIRECTORY, 'master.csv')
DEFAULT_SEARCH_RADIUS = 25
DEFAULT_MAX_LISTING_DAYS = 60
DEFAULT_DELAY_MAX_DURATION = 5.0
DEFAULT_DELAY_MIN_DURATION = 1.0
DEFAULT_DELAY_ALGORITHM = DelayAlgorithm.LINEAR
# FIXME: re-enable glassdoor once we fix issue with it. (#87)
DEFAULT_PROVIDERS = [Provider.MONSTER, Provider.INDEED] #, Provider.GLASSDOOR]
DEFAULT_PROVIDER_NAMES = [p.name for p in DEFAULT_PROVIDERS]
DEFAULT_NO_SCRAPE = False
DEFAULT_USE_WEB_DRIVER = False
DEFAULT_RECOVER = False
DEFAULT_RETURN_SIMILAR_RESULTS = False
DEFAULT_SAVE_DUPLICATES = False
DEFAULT_RANDOM_DELAY = False
DEFAULT_RANDOM_CONVERGING_DELAY = False

# Defaults we use from localization, the scraper can always override it.
DEFAULT_DOMAIN_FROM_LOCALE = {
    Locale.CANADA_ENGLISH: 'ca',
    Locale.CANADA_FRENCH: 'ca',
    Locale.USA_ENGLISH: 'com',
}
