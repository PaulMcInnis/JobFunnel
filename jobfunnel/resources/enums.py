from enum import Enum

class Locale(Enum):
    """This will allow Scrapers / Filters / Main to identify the support they
    have for different domains of different websites

    Locale must be set as it defines the code implementation to use for forming
    the correct GET requests, to allow us to interact with a job-source.

    NOTE: add locales here as you need them, we do them per-country per-language
    becuase scrapers are written per-language-per-country as this matches how
    the information is served by job websites.
    """
    CANADA_ENGLISH = 1
    CANADA_FRENCH = 2
    USA_ENGLISH = 3

class JobStatus(Enum):
    """Job statuses that are built-into jobfunnel
    NOTE: these are the only valid values for entries in 'status' in our CSV
    """
    UNKNOWN = 1
    NEW = 2
    ARCHIVE = 3
    INTERVIEWING = 4
    INTERVIEWED = 5
    REJECTED = 6
    ACCEPTED = 7
    DELETE = 8
    INTERESTED = 9
    APPLIED = 10
    APPLY = 11
    OLD = 12


class JobField(Enum):
    """Fields of job that we need setters for, passed to Scraper.get(field=...)
    """
    TITLE = 0
    COMPANY = 1
    LOCATION = 2
    DESCRIPTION = 3
    KEY_ID = 4
    URL = 5
    LOCALE = 6
    QUERY = 7
    PROVIDER = 8
    STATUS = 9
    SCRAPE_DATE = 10
    SHORT_DESCRIPTION = 11
    POST_DATE = 12
    RAW = 13
    TAGS = 14


class Provider(Enum):
    """Job source providers
    """
    INDEED = 1
    GLASSDOOR = 2
    MONSTER = 3


class DelayAlgorithm(Enum):
    """delaying algorithms
    """
    CONSTANT = 1
    SIGMOID = 2
    LINEAR = 3
