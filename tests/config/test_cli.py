"""Test CLI parsing --> config dict
"""

import os

import pytest

from jobfunnel.config import build_config_dict, parse_cli
from tests.conftest import get_data_path

TEST_YAML = os.path.join(get_data_path(), "test_config.yml")
INCORRECT_TEST_YAML = os.path.join(get_data_path(), "../data/incorrect_test_config.yml")

inline_args = [
    # Test schema from CLI
    (
        [
            "inline",
            "-csv",
            "TEST_search",
            "-log-level",
            "DEBUG",
            "-cache",
            "TEST_cache",
            "-blf",
            "TEST_block_list",
            "-dl",
            "TEST_duplicates_list",
            "-log-file",
            "TEST_log_file",
            "-kw",
            "I",
            "Am",
            "Testing",
            "-l",
            "CANADA_ENGLISH",
            "-ps",
            "TESTPS",
            "-c",
            "TestCity",
            "-cbl",
            "Blocked Company",
            "Blocked Company 2",
            "-p",
            "INDEED",
            "MONSTER",
            "-r",
            "42",
            "-max-listing-days",
            "44",
            "--similar-results",
            "--random",
            "--converging",
            "-max",
            "8",
            "-min",
            "2",
            "-algorithm",
            "LINEAR",
        ]
    ),
]

load_args = [
    # Test schema from YAML
    (["load", "-s", TEST_YAML]),
    # Test overrideable args
    (["load", "-s", TEST_YAML, "-log-level", "DEBUG"]),
    (["load", "-s", TEST_YAML, "--no-scrape"]),
]

load_args_invalid_settings = [
    # Test incorrect yaml
    (["load", "-s", INCORRECT_TEST_YAML], ValueError),
]

invalid_args = [
    # Invalid cases
    (["load"], SystemExit),
    (["load", "-csv", "boo"], SystemExit),
    (
        [
            "-l",
            "CANADA_ENGLISH",
            "-ps",
            "TESTPS",
            "-c",
            "TestCity",
            "-cbl",
            "Blocked Company",
            "Blocked Company 2",
            "-p",
            "INDEED",
            "MONSTER",
            "-r",
            "42",
            "-max-listing-days",
            "44",
            "--similar-results",
            "--random",
            "--converging",
            "-max",
            "8",
            "-min",
            "2",
            "-algorithm",
            "LINEAR",
        ],
        SystemExit,
    ),
    (
        [
            "inline",
            "-csv",
            "TEST_search",
            "-log-level",
            "DEBUG",
            "-cache",
            "TEST_cache",
            "-blf",
            "TEST_block_list",
            "-dl",
            "TEST_duplicates_list",
        ],
        SystemExit,
    ),
    (["-csv", "test.csv"], SystemExit),
]


@pytest.mark.parametrize("argv", inline_args)
def test_parse_cli_inline(argv):
    """
    Test the correctness of parse_cli
    """
    args = parse_cli(argv)
    assert args["do_recovery_mode"] is False
    assert args["load | inline"] == "inline"
    assert args["log_level"] == "DEBUG"
    assert args["no_scrape"] is False
    assert args["master_csv_file"] == "TEST_search"
    assert args["log_file"] == "TEST_log_file"
    assert args["cache_folder"] == "TEST_cache"
    assert args["block_list_file"] == "TEST_block_list"
    assert args["duplicates_list_file"] == "TEST_duplicates_list"
    assert args["search.keywords"] == ["I", "Am", "Testing"]
    assert args["search.locale"] == "CANADA_ENGLISH"
    assert args["search.province_or_state"] == "TESTPS"
    assert args["search.city"] == "TestCity"
    assert args["search.company_block_list"] == ["Blocked Company", "Blocked Company 2"]
    assert args["search.radius"] == 42
    assert args["search.remoteness"] == "ANY"
    assert args["search.max_listing_days"] == 44
    assert args["search.similar_results"] is True
    assert args["proxy.protocol"] is None
    assert args["proxy.ip"] is None
    assert args["proxy.port"] is None
    assert args["delay.random"] is True
    assert args["delay.converging"] is True
    assert args["delay.max_duration"] == 8.0
    assert args["delay.min_duration"] == 2.0
    assert args["delay.algorithm"] == "LINEAR"


@pytest.mark.parametrize("argv", load_args)
def test_parse_cli_load(argv):
    args = parse_cli(argv)
    # FIXME: This test should only be testing the correctness of parse_cli
    # Assertions

    assert args["settings_yaml_file"] == TEST_YAML

    if "-log-level" in argv and argv[4] == "DEBUG":
        # NOTE: need to always pass log level in same place for this cdtn
        assert args["log_level"] == "DEBUG"
    if "--no-scrape" in argv:
        assert args["no_scrape"] is True
    else:
        assert args["no_scrape"] is False


@pytest.mark.parametrize("argv, exception", invalid_args)
def test_parse_cli_invalid_args(argv, exception):
    with pytest.raises(exception) as e:
        args = parse_cli(argv)
        assert args is not None  # TODO: Remove after test is fixed
    assert str(e.value) == "2"


@pytest.mark.parametrize("argv, exception", load_args_invalid_settings)
def test_build_config_dict_invalid_settings(argv, exception):
    args = parse_cli(argv)
    with pytest.raises(exception) as e:
        cfg_dict = build_config_dict(args)
        assert cfg_dict is not None  # TODO: Remove after test is fixed
    assert (
        str(e.value) == "Invalid Config settings yaml:\n"
        "{'search': [{'radius': ['must be of integer type']}]}"
    )


@pytest.mark.parametrize("argv", load_args)
def test_build_config_dict_load_args(argv):
    args = parse_cli(argv)
    cfg_dict = build_config_dict(args)

    assert cfg_dict["master_csv_file"] == "TEST_search"
    assert cfg_dict["cache_folder"] == "TEST_cache"
    assert cfg_dict["block_list_file"] == "TEST_block_list"
    assert cfg_dict["duplicates_list_file"] == "TEST_duplicates_list"
    assert cfg_dict["log_file"] == "TEST_log_file"
    assert cfg_dict["search"] == {
        "locale": "CANADA_ENGLISH",
        "providers": ["INDEED", "MONSTER"],
        "province_or_state": "TESTPS",
        "city": "TestCity",
        "radius": 42,
        "keywords": ["I", "Am", "Testing"],
        "max_listing_days": 44,
        "company_block_list": ["Blocked Company", "Blocked Company 2"],
        "similar_results": False,
        "remoteness": "ANY",
    }
    if "-log-level" in argv:
        assert cfg_dict["log_level"] == "DEBUG"
    else:
        assert cfg_dict["log_level"] == "INFO"

    assert cfg_dict["delay"] == {
        "algorithm": "LINEAR",
        "max_duration": 8,
        "min_duration": 2,
        "random": True,
        "converging": True,
    }
    if "--no-scrape" in argv:
        assert cfg_dict["no_scrape"] is True
    else:
        assert cfg_dict["no_scrape"] is False


@pytest.mark.parametrize("argv", inline_args)
def test_build_config_dict_inline_args(argv):
    args = parse_cli(argv)
    cfg_dict = build_config_dict(args)
    assert cfg_dict["master_csv_file"] == "TEST_search"
    assert cfg_dict["cache_folder"] == "TEST_cache"
    assert cfg_dict["block_list_file"] == "TEST_block_list"
    assert cfg_dict["duplicates_list_file"] == "TEST_duplicates_list"
    assert cfg_dict["log_file"] == "TEST_log_file"
    assert cfg_dict["search"] == {
        "locale": "CANADA_ENGLISH",
        "providers": ["INDEED", "MONSTER"],
        "province_or_state": "TESTPS",
        "city": "TestCity",
        "radius": 42,
        "keywords": ["I", "Am", "Testing"],
        "max_listing_days": 44,
        "company_block_list": ["Blocked Company", "Blocked Company 2"],
        "similar_results": True,
        "remoteness": "ANY",
    }
    assert cfg_dict["delay"] == {
        "random": True,
        "converging": True,
        "max_duration": 8.0,
        "min_duration": 2.0,
        "algorithm": "LINEAR",
    }
    assert cfg_dict["log_level"] == "DEBUG"
    assert cfg_dict["no_scrape"] is False
    assert cfg_dict["proxy"] == {}
