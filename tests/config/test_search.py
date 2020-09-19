"""Test the search config
"""
import pytest

from jobfunnel.config import SearchConfig
from jobfunnel.resources import Locale


@pytest.mark.parametrize("keywords, exp_query_str", [
    (['b33f', 'd3ad'], 'b33f d3ad'),
    (['trumpet'], 'trumpet'),
])
def test_search_config_query_string(mocker, keywords, exp_query_str):
    """Test that search config can build keyword query string correctly.
    """
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


@pytest.mark.parametrize("locale, domain, exp_domain", [
    (Locale.CANADA_ENGLISH, None, 'ca'),
    (Locale.CANADA_FRENCH, None, 'ca'),
    (Locale.USA_ENGLISH, None, 'com'),
    (Locale.UK_ENGLISH, None, 'co.uk'),
    (Locale.USA_ENGLISH, 'xyz', 'xyz'),
    (None, None, None),
])
def test_search_config_init(mocker, locale, domain, exp_domain):
    """Make sure the init functions as we expect wrt to domain selection
    """
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
