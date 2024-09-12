from enum import Enum


class Locale(Enum):
    """This will allow Scrapers / Filters / Main to identify the support they
    have for different domains of different websites

    Locale must be set as it defines the code implementation to use for forming
    the correct GET requests, to allow us to interact with a job-source.
    """

    CANADA_ENGLISH = 1
    CANADA_FRENCH = 2
    USA_ENGLISH = 3
    UK_ENGLISH = 4
    FRANCE_FRENCH = 5
    GERMANY_GERMAN = 6


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
    """Fields of job that we need setters for, passed to Scraper.get(field=...)"""

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
    WAGE = 15
    REMOTENESS = 16


class Remoteness(Enum):
    """What level of remoteness is a Job?"""

    UNKNOWN = 1  # NOTE: invalid state
    IN_PERSON = 2
    TEMPORARILY_REMOTE = 3  # AKA Cuz' COVID, realistically this is not remote!
    PARTIALLY_REMOTE = 4
    FULLY_REMOTE = 5
    ANY = 6


class DuplicateType(Enum):
    """Ways in which a job can be a duplicate
    NOTE: we use these to determine what action(s) to take for a duplicate
    """

    KEY_ID = 0
    EXISTING_TFIDF = 1
    NEW_TFIDF = 2


class Provider(Enum):
    """Job source providers"""

    INDEED = 1
    GLASSDOOR = 2
    MONSTER = 3


class DelayAlgorithm(Enum):
    """delaying algorithms"""

    CONSTANT = 1
    SIGMOID = 2
    LINEAR = 3
