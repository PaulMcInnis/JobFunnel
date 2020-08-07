"""Constant definitions or files we need to load once can go here
"""
import os
import string
from pathlib import Path

# CSV header for output CSV. do not remove anything or you'll break usr's CSV's
# TODO: need to add short and long descriptions (breaking change)
CSV_HEADER = [
    'status', 'title', 'company', 'location', 'date', 'blurb', 'tags', 'link',
    'id', 'provider', 'query', 'locale'
]

# Maximum num threads we use when scraping
MAX_CPU_WORKERS = 8

# Default args
DEFAULT_SEARCH_RADIUS_KM = 25
DEFAULT_MAX_LISTING_DAYS = 60

# Other definitions
USER_HOME_DIRECTORY = os.path.abspath(str(Path.home()))
DEFAULT_OUTPUT_DIRECTORY = os.path.join(
    USER_HOME_DIRECTORY, 'job_search_results'
)
DEFAULT_CACHE_DIRECTORY = os.path.join(DEFAULT_OUTPUT_DIRECTORY, '.cache')

PRINTABLE_STRINGS = set(string.printable)

# Load the user agent list once only.
USER_AGENT_LIST_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'user_agent_list.txt')
)
USER_AGENT_LIST = []
with open(USER_AGENT_LIST_FILE) as file:
    for line in file:
        li = line.strip()
        if li and not li.startswith("#"):
            USER_AGENT_LIST.append(line.rstrip('\n'))
