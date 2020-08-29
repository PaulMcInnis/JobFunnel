"""Test the config library
"""
import pytest

from jobfunnel.config import (DelayConfig, JobFunnelConfigManager, ProxyConfig,
                              SearchConfig)
from jobfunnel.resources import DelayAlgorithm
from jobfunnel.resources import Locale


@pytest.mark.parametrize("max_duration, min_duration, invalid_dur", [
    (1.0, 1.0, True),
    (-1.0, 1.0, True),
    (5.0, 0.0, True),
    (5.0, 1.0, False),
])
@pytest.mark.parametrize("random, converge, invalid_rand", [
    (True, True, False),
    (True, False, False),
    (False, True, True),
])
@pytest.mark.parametrize("delay_algorithm", (DelayAlgorithm.LINEAR, None))
def test_delay_config_validate(max_duration, min_duration, invalid_dur,
                               delay_algorithm, random, converge, invalid_rand):
    """Test DelayConfig
    TODO: test messages too
    """
    cfg = DelayConfig(
        max_duration=max_duration,
        min_duration=min_duration,
        algorithm=delay_algorithm,
        random=random,
        converge=converge,
    )

    # FUT
    if invalid_dur or not delay_algorithm or invalid_rand:
        with pytest.raises(ValueError):
            cfg.validate()
    else:
        cfg.validate()


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


# TODO: implement once we add validation to ProxyConfig
# def test_proxy_config(protocol, ip_address, port):
#     pass

# FIXME: need to break down config manager stuff, perhaps it shouldn't be
# creating the paths in it's init. Makes this test complicated.
# @pytest.mark.parametrize('pass_del_cfg', (True, False))
# def test_config_manager_init(mocker, pass_del_cfg):
#     """NOTE: unlike other configs this one validates itself on creation
#     """
#     # Mocks
#     patch_del_cfg = mocker.patch('jobfunnel.config.manager.DelayConfig')
#     patch_os = mocker.patch('jobfunnel.config.manager.os')
#     patch_os.path.exists.return_value = False  # check it makes all paths
#     mock_master_csv = mocker.Mock()
#     mock_block_list = mocker.Mock()
#     mock_dupe_list = mocker.Mock()
#     mock_cache_folder = mocker.Mock()
#     mock_search_cfg = mocker.Mock()
#     mock_proxy_cfg = mocker.Mock()
#     mock_del_cfg = mocker.Mock()

#     # FUT
#     cfg = JobFunnelConfigManager(
#         master_csv_file=mock_master_csv,
#         user_block_list_file=mock_block_list,
#         duplicates_list_file=mock_dupe_list,
#         cache_folder=mock_cache_folder,
#         search_config=mock_search_cfg,
#         delay_config=mock_del_cfg if pass_del_cfg else None,
#         proxy_config=mock_proxy_cfg,
#         log_file='', # TODO optional?
#     )

#     # Assertions
