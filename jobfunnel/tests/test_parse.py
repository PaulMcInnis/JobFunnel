import pytest
import sys

from unittest.mock import patch

from ..config.parser import parse_config


def test_user_yaml():
    with patch.object(sys, 'argv', ['', '-s', 'jobfunnel/tests/settings/settings1.yaml']):
        config = parse_config()

        assert config['output_path'] == "fish"
        assert set(config['providers']) == set(['indeed', 'monster'])
        assert config['search_terms']['region']['state'] == 'NY'
        # assert config['search_terms']['region']['province'] == 'NY' # I believe this should pass
        assert config['search_terms']['region']['city'] == 'New York'
        assert config['search_terms']['region']['domain'] == 'com'
        assert config['search_terms']['region']['radius'] == 25


def test_cli_yaml():
    with patch.object(sys, 'argv', ['', '--no_delay']):
        config = parse_config()
        assert config['set_delay'] == False


def test_config_fail():
    with patch.object(sys, 'argv', ['', '-s', 'jobfunnel/tests/settings/settings_fail.yaml']):
        with pytest.raises(KeyError):
            config = parse_config()
