"""Test the search config
"""

import pytest

from jobfunnel.config import SearchConfig
from jobfunnel.resources import Locale, Remoteness, enums


@pytest.mark.parametrize(
    "keywords, exp_query_str",
    [
        (["b33f", "d3ad"], "b33f d3ad"),
        (["trumpet"], "trumpet"),
    ],
)
def test_search_config_query_string(mocker, keywords, exp_query_str):
    """Test that search config can build keyword query string correctly."""
    cfg = SearchConfig(
        keywords=keywords,
        province_or_state=mocker.Mock(),
        locale=Locale.CANADA_FRENCH,
        providers=mocker.Mock(),
    )

    # FUT
    query_str = cfg.query_string

    # Assertions
    assert query_str == exp_query_str


@pytest.mark.parametrize(
    "locale, domain, exp_domain",
    [
        (Locale.CANADA_ENGLISH, None, "ca"),
        (Locale.CANADA_FRENCH, None, "ca"),
        (Locale.USA_ENGLISH, None, "com"),
        (Locale.UK_ENGLISH, None, "co.uk"),
        (Locale.FRANCE_FRENCH, None, "fr"),
        (Locale.GERMANY_GERMAN, None, "de"),
        (Locale.USA_ENGLISH, "xyz", "xyz"),
        (None, None, None),
    ],
)
def test_search_config_init(mocker, locale, domain, exp_domain):
    """Make sure the init functions as we expect wrt to domain selection"""
    # FUT
    if not locale:
        # test our error
        with pytest.raises(ValueError, match=r"Unknown domain for locale.*"):
            cfg = SearchConfig(
                keywords=mocker.Mock(),
                province_or_state=mocker.Mock(),
                locale=-1,  # AKA an unknown Enum entry to Locale
                providers=mocker.Mock(),
            )
    else:
        cfg = SearchConfig(
            keywords=mocker.Mock(),
            province_or_state=mocker.Mock(),
            locale=locale,
            domain=domain,
            providers=mocker.Mock(),
        )

        # Assertions
        assert cfg.domain == exp_domain


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city",
    [
        (
            ["Ice Cream", "Spiderman"],
            None,
            Locale.USA_ENGLISH,
            [enums.Provider.INDEED],
            "Austin",
        )
    ],
)
def test_search_config_validate_invalid_province(
    keywords, province_or_state, locale, providers, in_city
):
    cfg = SearchConfig(keywords, province_or_state, locale, providers, city=in_city)

    with pytest.raises(AssertionError, match="Province/State not set"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city",
    [(["Python", "Space"], "Texas", Locale.USA_ENGLISH, [enums.Provider.INDEED], None)],
)
def test_search_config_validate_invalid_city(
    keywords, province_or_state, locale, providers, in_city
):
    cfg = SearchConfig(keywords, province_or_state, locale, providers, city=in_city)

    with pytest.raises(AssertionError, match="City not set"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state,  locale, providers, in_city,  in_domain",
    [(["Python", "Space"], "Texas", None, [enums.Provider.INDEED], "Austin", "com")],
)
def test_search_config_validate_invalid_locale(
    keywords, province_or_state, locale, providers, in_city, in_domain
):
    cfg = SearchConfig(
        keywords, province_or_state, locale, providers, city=in_city, domain=in_domain
    )

    with pytest.raises(AssertionError, match="Locale not set"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city",
    [(["Ice Cream", "Spiderman"], "Texas", Locale.USA_ENGLISH, [], "Austin")],
)
def test_search_config_validate_invalid_providers(
    keywords, province_or_state, locale, providers, in_city
):
    cfg = SearchConfig(keywords, province_or_state, locale, providers, city=in_city)

    with pytest.raises(AssertionError, match="Providers not set"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city",
    [([], "Texas", Locale.USA_ENGLISH, [enums.Provider.INDEED], "Austin")],
)
def test_search_config_validate_invalid_keywords(
    keywords, province_or_state, locale, providers, in_city
):
    cfg = SearchConfig(keywords, province_or_state, locale, providers, city=in_city)

    with pytest.raises(AssertionError, match="Keywords not set"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city, in_max_listing_days",
    [
        (
            ["Ice Cream", "Spiderman"],
            Locale.USA_ENGLISH,
            Locale.USA_ENGLISH,
            [enums.Provider.INDEED],
            "Austin",
            -1,
        )
    ],
)
def test_search_config_validate_invalid_max_posting_days(
    keywords, province_or_state, locale, providers, in_city, in_max_listing_days
):
    cfg = SearchConfig(
        keywords,
        province_or_state,
        locale,
        providers,
        city=in_city,
        max_listing_days=in_max_listing_days,
    )

    with pytest.raises(AssertionError, match="Cannot set max posting days < 1"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city",
    [
        (
            ["Ice Cream", "Spiderman"],
            "Texas",
            Locale.USA_ENGLISH,
            [enums.Provider.INDEED],
            "Austin",
        )
    ],
)
def test_search_config_validate_domain(
    keywords, province_or_state, locale, providers, in_city
):
    cfg = SearchConfig(keywords, province_or_state, locale, providers, city=in_city)

    # We have to force an invalid domain because the constructor ensures that it is valid.
    cfg.domain = None

    with pytest.raises(AssertionError, match="Domain not set"):
        cfg.validate()


@pytest.mark.parametrize(
    "keywords, province_or_state, locale, providers, in_city, in_remoteness",
    [
        (
            ["Ice Cream", "Spiderman"],
            "Texas",
            Locale.USA_ENGLISH,
            [enums.Provider.INDEED],
            "Austin",
            Remoteness.UNKNOWN,
        )
    ],
)
def test_search_config_validate_remoteness(
    keywords, province_or_state, locale, providers, in_city, in_remoteness
):
    cfg = SearchConfig(
        keywords,
        province_or_state,
        locale,
        providers,
        city=in_city,
        remoteness=in_remoteness,
    )

    with pytest.raises(AssertionError, match="Remoteness is UNKNOWN!"):
        cfg.validate()
