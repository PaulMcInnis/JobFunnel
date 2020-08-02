"""Place to store Enums and such for localization / internationalization
"""
from enum import Enum
from typing import List, Optional


class Locale(Enum):
    """This will allow Scrapers / Filters / Main to identify the support they
    have for different domains of different websites

    TODO: better way using the locale module?
    """
    CANADA_ENGLISH = 1
    CANADA_FRENCH = 2
    USA_ENGLISH = 3


def get_domain_from_locale(locale: Locale) -> str:
    """Get a domain string from the locale Enum

    TODO: we may want something more flexible in the future.
    """
    if locale in [Locale.CANADA_ENGLISH, Locale.CANADA_FRENCH]:
        return 'ca'
    elif locale == Locale.USA_ENGLISH:
        return 'com'
    else:
        raise ValueError(f"Unknown domain string for locale {locale}")

