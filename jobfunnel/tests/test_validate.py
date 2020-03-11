import pytest
import sys

from unittest.mock import patch

from ..config.parser import parse_config
from ..config.validate import validate_config, validate_delay, validate_region
from ..tools.tools import config_factory

with patch.object(sys, 'argv', ['']):
    config = parse_config()


# define config dictionaries that are not valid
# invalid path

attr_list = [
    [['master_list_path'], 'masterzz_list.csv'],
    [['providers'], ['indeed', 'twitter']],
    [['search_terms', 'region', 'domain'], 'cjas'],
    [['search_terms', 'region', 'province'], None],
    [['delay_config', 'function'], 'weird'],
    [['delay_config', 'min_delay'], 50.0],
    [['delay_config', 'min_delay'], -1],
    [['delay_config', 'delay'], 2],
    [['max_listing_days'], -1],
    [['data_path'], 'data_dump'],
    [['duplicate_list_path'], 'duplicate_list_.csv'],
    [['log_path'], 'data/jobfunnel_.log'],
    [['filter_list_path'], 'data/filter_list_.json']
]

configs = config_factory(config, attr_list)


# Test all paths with invalid values

path_configs = config_factory(config, attr_list[12: 13])
@pytest.mark.parametrize('config', path_configs)
def test_filter_list_path_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'filter_list_path'


path_configs = config_factory(config, attr_list[11: 12])
@pytest.mark.parametrize('config', path_configs)
def test_log_path_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'log_path'


path_configs = config_factory(config, attr_list[10: 11])
@pytest.mark.parametrize('config', path_configs)
def test_duplicate_list_path_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'duplicate_list_path'


path_configs = config_factory(config, attr_list[9: 10])
@pytest.mark.parametrize('config', path_configs)
def test_data_path_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'data_path'


path_configs = config_factory(config, attr_list[0: 1])
@pytest.mark.parametrize('config', path_configs)
def test_master_list_path_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'master_list_path'


# test with invalid providers

providers_config = config_factory(config, attr_list[1: 2])


@pytest.mark.parametrize('config', providers_config)
def test_providers_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'providers'


# test with invalid regions and domains

region_config = config_factory(config, attr_list[2:3])


@pytest.mark.parametrize('config', region_config)
def test_domain_fail(config):
    with pytest.raises(Exception) as e:
        validate_region(config['search_terms']['region'])
    assert str(e.value) == 'domain'


region_config = config_factory(config, attr_list[3:4])


@pytest.mark.parametrize('config', region_config)
def test_province_fail(config):
    with pytest.raises(Exception) as e:
        validate_region(config['search_terms']['region'])
    assert str(e.value) == 'province'


# test validate_region with the default valid Configuration

def test_region_pass():
    validate_region(config['search_terms']['region'])


# generate config with invalid delay function name

delay_configs = config_factory(config, attr_list[4: 5])


@pytest.mark.parametrize('config', delay_configs)
def test_delay_function_fail(config):
    with pytest.raises(Exception) as e:
        validate_delay(config['delay_config'])
    assert str(e.value) == 'delay_function'


# test delay_function with original configuration

def test_delay_function_pass():
    validate_delay(config['delay_config'])


# generate config with invalid min delay value of -1

delay_configs = config_factory(config, attr_list[6: 7])


@pytest.mark.parametrize('config', delay_configs)
def test_delay_min_delay_fail(config):
    with pytest.raises(Exception) as e:
        validate_delay(config['delay_config'])
    assert str(e.value) == '(min)_delay'


# Test validate_delay with a min_delay greater than delay

delay_configs = config_factory(config, attr_list[5: 6])


@pytest.mark.parametrize('config', delay_configs)
def test_delay_min_delay_greater_than_delay_fail(config):
    with pytest.raises(Exception) as e:
        validate_delay(config['delay_config'])
    assert str(e.value) == '(min)_delay'


# Test validate_delay with a delay less than 10(the minimum)

delay_configs = config_factory(config, attr_list[7: 8])


@pytest.mark.parametrize('config', delay_configs)
def test_delay_less_than_10_fail(config):
    with pytest.raises(Exception) as e:
        validate_delay(config['delay_config'])
    assert str(e.value) == '(min)_delay'


# Test validate_delay with the original configuration

def test_delay_pass():
    validate_delay(config['delay_config'])


# test validate_delay with a max_listing_days value of -1

max_listing_days_config = config_factory(config, attr_list[8: 9])


@pytest.mark.parametrize('config', max_listing_days_config)
def test_delay_max_listing_days_fail(config):
    with pytest.raises(Exception) as e:
        validate_config(config)
    assert str(e.value) == 'max_listing_days'


# Test the integration of all parts with the config as a whole

@pytest.mark.parametrize('config', configs)
def test_config_fail(config):
    with pytest.raises(Exception):
        validate_config(config)


def test_config_pass():
    validate_config(config)
