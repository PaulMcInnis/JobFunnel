import pytest
import sys

from ..config.parser import parse_config
from ..config.validate import validate_config
from ..tools.tools import change_nested_dict, config_factory

sys.argv = ['']
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
]

configs = config_factory(config, attr_list)


@pytest.mark.parametrize('config', configs)
def test_config(config):
    with pytest.raises(Exception):
        validate_config(config)
