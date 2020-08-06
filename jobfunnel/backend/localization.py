"""Place to store Enums and such for localization / internationalization
"""
from enum import Enum
from typing import List, Optional


class Locale(Enum):
    """This will allow Scrapers / Filters / Main to identify the support they
    have for different domains of different websites

    NOTE: add locales here as you need them, we do them per-country per-language
    becuase scrapers are written per-language-per-country as this matches
    how the information is served by job websites.
    """
    UNKNOWN = 1
    CANADA_ENGLISH = 2
    CANADA_FRENCH = 3
    CANADA_MANDARIN = 4
    CANADA_CANTONESE = 5
    CANADA_PUNJABI = 6
    CANADA_SPANISH = 7
    USA_ENGLISH = 4


def get_domain_from_locale(locale: Locale) -> str:
    """Get a domain string from the locale Enum

    NOTE: if you want to override this you can always set domain in headers
    directly without using this method
    """
    if locale in [Locale.CANADA_ENGLISH, Locale.CANADA_FRENCH]:
        return 'ca'
    elif locale == Locale.USA_ENGLISH:
        return 'com'
    else:
        raise ValueError(f"Unknown domain string for locale {locale}")
