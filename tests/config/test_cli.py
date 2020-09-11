"""Test CLI parsing --> config dict
"""
import os
import pytest
from jobfunnel.config import parse_cli, build_config_dict


TEST_YAML = os.path.join('tests', 'data', 'test_config.yml')


@pytest.mark.parametrize('argv, exp_exception', [
    # Test schema from YAML
    (['load', '-s', TEST_YAML], None),
    # Test overrideable args
    (['load', '-s', TEST_YAML, '-log-level', 'DEBUG'], None),
    (['load', '-s', TEST_YAML, '-log-level', 'WARNING'], None),
    (['load', '-s', TEST_YAML, '--no-scrape'], None),
    # Test schema from CLI
    (['inline', '-csv', 'TEST_search', '-log-level', 'DEBUG', '-cache',
      'TEST_cache', '-blf', 'TEST_block_list', '-dl', 'TEST_duplicates_list',
      '-log-file', 'TEST_log_file', '-kw', 'I', 'Am', 'Testing', '-l',
      'CANADA_ENGLISH', '-ps', 'TESTPS', '-c', 'TestCity', '-cbl',
      'Blocked Company', 'Blocked Company 2', '-p', 'INDEED', 'MONSTER',
      '-r', '42', '-max-listing-days', '44', '--similar-results', '--random',
      '--converging', '-max', '8', '-min', '2', '-algorithm', 'LINEAR'], None),
    # Invalid cases
    (['load'], SystemExit),
    (['load', '-csv', 'boo'], SystemExit),
    (['inline', '-csv', 'TEST_search', '-log-level', 'DEBUG', '-cache',
      'TEST_cache', '-blf', 'TEST_block_list', '-dl',
      'TEST_duplicates_list'], SystemExit),
    (['-csv', 'test.csv'], SystemExit),
    (['-l',
      'CANADA_ENGLISH', '-ps', 'TESTPS', '-c', 'TestCity', '-cbl',
      'Blocked Company', 'Blocked Company 2', '-p', 'INDEED', 'MONSTER',
      '-r', '42', '-max-listing-days', '44', '--similar-results', '--random',
      '--converging', '-max', '8', '-min', '2', '-algorithm',
      'LINEAR'], SystemExit),
])
def test_parse_cli_build_config_dict(argv, exp_exception):
    """Functional test to ensure that the CLI functions as we expect
    TODO: break down into test_parse_cli and test_config_parser
    FIXME: add exception message assertions
    """
    # FUT
    if exp_exception:
        with pytest.raises(exp_exception):
            args = parse_cli(argv)
            cfg = build_config_dict(args)
    else:
        args = parse_cli(argv)
        cfg = build_config_dict(args)

        # Assertions
        assert cfg['master_csv_file'] == 'TEST_search'
        assert cfg['cache_folder'] == 'TEST_cache'
        assert cfg['block_list_file'] == 'TEST_block_list'
        assert cfg['duplicates_list_file'] == 'TEST_duplicates_list'
        assert cfg['search']['locale'] == 'CANADA_ENGLISH'
        assert cfg['search']['providers'] == ['INDEED', 'MONSTER']
        assert cfg['search']['province_or_state'] == 'TESTPS'
        assert cfg['search']['city'] == 'TestCity'
        assert cfg['search']['radius'] == 42
        assert cfg['search']['keywords'] == ['I', 'Am', 'Testing']
        assert cfg['search']['max_listing_days'] == 44
        assert cfg['search']['company_block_list'] == ['Blocked Company',
                                                       'Blocked Company 2']
        if '-log-level' in argv:
            # NOTE: need to always pass log level in same place for this cdtn
            assert cfg['log_level'] == argv[4]
        else:
            assert cfg['log_level'] == 'INFO'
        if '--no-scrape' in argv:
            assert cfg['no_scrape']
        else:
            assert not cfg['no_scrape']
        if '--similar-results' in argv:
            assert cfg['search']['similar_results']
        else:
            assert not cfg['search']['similar_results']

        assert cfg['delay']['algorithm'] == 'LINEAR'
        assert cfg['delay']['max_duration'] == 8
        assert cfg['delay']['min_duration'] == 2
        assert cfg['delay']['random']
        assert cfg['delay']['converging']
