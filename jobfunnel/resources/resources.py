"""String-like resouces and other constants are initialized here.
"""

import datetime
from pathlib import Path
import string

# CSV header for output CSV. do not remove anything or you'll break usr's CSV's
# TODO: need to add short and long descriptions (breaking change)
CSV_HEADER = [
    "status",
    "title",
    "company",
    "location",
    "date",
    "blurb",
    "tags",
    "link",
    "id",
    "provider",
    "query",
    "locale",
    "wage",
    "remoteness",
]

LOG_LEVEL_NAMES = ["CRITICAL", "FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]

MIN_DESCRIPTION_CHARS = 5  # If Job.description is less than this we fail valid.
MAX_CPU_WORKERS = 8  # Maximum num threads we use when scraping
MIN_JOBS_TO_PERFORM_SIMILARITY_SEARCH = 25  # Minimum # of jobs we need to TFIDF
MAX_BLOCK_LIST_DESC_CHARS = 150  # Maximum len of description in block_list JSON
DEFAULT_MAX_TFIDF_SIMILARITY = 0.75  # Maximum similarity between job text TFIDF

BS4_PARSER = "lxml"
T_NOW = datetime.datetime.today()  # NOTE: use today so we only compare days

PRINTABLE_STRINGS = set(string.printable)


def load_user_agents(file_path):
    """Loads user agent strings from a file, skipping comments and blank lines."""
    try:
        with open(file_path, "r") as file:
            return [
                line.strip()
                for line in file
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return []


# Define the paths
USER_AGENT_LIST_FILE = Path(__file__).parent / "user_agent_list.txt"
USER_AGENT_LIST_MOBILE_FILE = Path(__file__).parent / "user_agent_list_mobile.txt"

# Load the lists
USER_AGENT_LIST = load_user_agents(USER_AGENT_LIST_FILE)
USER_AGENT_LIST_MOBILE = load_user_agents(USER_AGENT_LIST_MOBILE_FILE)
