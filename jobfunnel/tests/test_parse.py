import pytest
import sys
import os
import yaml

from unittest.mock import patch
from pathlib import Path

from ..config.parser import parse_config

config_dict = {
    'output_path': 'fish',
    'providers': ['Indeed', 'Monster'],
    'search_terms': {
        'region': {
            'state': 'NY',
            'city': 'New York',
            'domain': 'com',
        }
    }
}

config_dict_fail = {
    'this_should_fail': False
}

def test_user_yaml(tmpdir):
    # create temporary settings file and write yaml file
    yaml_file = Path(tmpdir) / 'settings.yaml'
    with open(yaml_file, mode='w') as f:
        yaml.dump(config_dict, f)

    # call funnel with user-defined settings
    with patch.object(sys, 'argv', ['', '-s', str(yaml_file)]):
        config = parse_config()

        assert config['output_path'] == "fish"
        assert set(config['providers']) == set(['indeed', 'monster'])
        assert config['search_terms']['region']['state'] == 'NY'
        # assert config['search_terms']['region']['province'] == 'NY' # I believe this should pass
        assert config['search_terms']['region']['city'] == 'New York'
        assert config['search_terms']['region']['domain'] == 'com'
        assert config['search_terms']['region']['radius'] == 25


def test_cli_yaml():
    with patch.object(sys, 'argv', ['', '--no_scrape']):
        config = parse_config()
        assert config['no_scrape'] is True


def test_config_fail(tmpdir):
    # create temporary settings file and write yaml file
    yaml_file = Path(tmpdir) / 'settings.yaml'
    with open(yaml_file, mode='w') as f:
        yaml.dump(config_dict_fail, f)

    # call funnel with user-defined settings
    with patch.object(sys, 'argv', ['', '-s', str(yaml_file)]):
        with pytest.raises(KeyError):
            config = parse_config()
