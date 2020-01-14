import pytest
import sys

from ..config.parser import parse_config
from ..config.validate import validate_config
from ..tools.tools import change_nested_dict, config_factory


def test_user_yaml():
    sys.argv[1] = '-s'
    sys.argv[2] = 'jobfunnel/tests/settings/settings1.yaml'
    config = parse_config()

    assert config['output_path'] == "fish"
    assert set(config['providers']) == set(['indeed', 'monster'])
    assert config['search_terms']['region']['state'] == 'NY'
    # assert config['search_terms']['region']['province'] == 'NY' # I believe this should pass
    assert config['search_terms']['region']['city'] == 'New York'
    assert config['search_terms']['region']['domain'] == 'com'
    assert config['search_terms']['region']['radius'] == 25

def test_cli_yaml():
    # TODO load --no_delay argument

    config = parse_config()

    # assert config['set_delay'] == False