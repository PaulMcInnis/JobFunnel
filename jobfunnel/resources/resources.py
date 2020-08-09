"""String-like resouces and other constants are initialized here.
"""
import os
import string

# CSV header for output CSV. do not remove anything or you'll break usr's CSV's
# TODO: need to add short and long descriptions (breaking change)
CSV_HEADER = [
    'status', 'title', 'company', 'location', 'date', 'blurb', 'tags', 'link',
    'id', 'provider', 'query', 'locale'
]

LOG_LEVEL_NAMES = [
    'CRITICAL', 'FATAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'
]

# Maximum num threads we use when scraping
MAX_CPU_WORKERS = 8
MAX_BLOCK_LIST_DESC_CHARS = 150  # Maximum len of description in block_list JSON

BS4_PARSER = 'lxml'

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
