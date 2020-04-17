import pytest
import sys
import os
import yaml

from pathlib import Path
from unittest.mock import patch

from jobfunnel.config.parser import parse_config, parse_cli, cli_to_yaml, update_yaml, check_config_types, log_levels


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

cli_options = [
    ['', '-s', 'settings.yaml'],
    ['', '-o', '.'],
    ['', '-kw', 'java', 'python'],
    ['', '-p', 'ON'],
    ['', '--city', 'New York'],
    ['', '--domain', 'com'],
    ['', '-r'],
    ['', '-c'],
    ['', '-d', '20'],
    ['', '-md', '10'],
    ['', '--fun', 'linear'],
    ['', '--log_level', 'info'],
    ['', '--similar'],
    ['', '--no_scrape'],
    # US proxy grabbed from https://www.free-proxy-list.net/
    ['', '--proxy', 'http://50.193.9.202:53888'],
    ['', '--recover'],
    ['', '--save_dup'],
    ['', '--max_listing_days', '30'],
]


# test parse_cli with all command line options

@pytest.mark.parametrize('option', cli_options)
def test_parse_cli_pass(option):
    with patch.object(sys, 'argv', option):
        config = parse_cli()


# test Parse_cli with an invalid argument

def test_parse_cli_fail():
    with patch.object(sys, 'argv', ['', 'invalid_arg']):
        with pytest.raises(SystemExit):
            config = parse_cli()


@pytest.mark.parametrize('option', cli_options)
def test_parse_cli_to_yaml_pass(option):
    with patch.object(sys, 'argv', option):
        cli = parse_cli()
        cli_to_yaml(cli)


# create config fixture to avoid code duplication

@pytest.fixture()
def config_dependency():
    def setup(default_path='config/settings.yaml', patch_path=None):
        """Does everything parse_config does up until loading the settings file passed in
        by the user, if they choose to pass one, to prepare the config dictionary for
        other tests to use. This fixture assumes that the tests
        test_parse_cli_* and test_parse_cli_to_yaml_* have passed.

        Returns the dictionary with keys 'config', 'given_yaml' and 'cli_yaml'

        It is ensured that config and given_yaml are valid, otherwise an exception is thrown.
        """
        # find the jobfunnel root dir
        jobfunnel_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), '../jobfunnel'))

        # load the default settings
        default_yaml_path = os.path.join(jobfunnel_path, default_path)
        default_yaml = yaml.safe_load(open(default_yaml_path, 'r'))

        # parse the command line arguments
        if patch_path == None:
            with patch.object(sys, 'argv', ['', '-s', default_yaml_path]):
                cli = parse_cli()
        else:
            with patch.object(sys, 'argv', ['', '-s', patch_path]):
                cli = parse_cli()
        cli_yaml = cli_to_yaml(cli)

        # parse the settings file for the line arguments
        given_yaml = None
        given_yaml_path = None
        if cli.settings is not None:
            given_yaml_path = os.path.dirname(cli.settings)
            given_yaml = yaml.safe_load(open(cli.settings, 'r'))

        config = default_yaml
        return {'config': config, 'given_yaml': given_yaml,
                'cli_yaml': cli_yaml}
    return setup


# test update_update_yaml with every command line option

@pytest.mark.parametrize('option', cli_options)
def test_update_yaml_pass(option, config_dependency):
    config_setup = config_dependency()
    with patch.object(sys, 'argv', option):
        # parse the command line arguments
        cli = parse_cli()
        cli_yaml = cli_to_yaml(cli)

        # parse the settings file for the line arguments
        given_yaml = None
        if cli.settings is not None:
            # take this opportunity to ensure that the demo settings file exists
            given_yaml = config_setup['given_yaml']

        # combine default, given and argument yamls into one. Note that we update
        # the values of the default_yaml, so we use this for the rest of the file.
        # We could make a deep copy if necessary.
        config = config_setup['config']

        if given_yaml is not None:
            update_yaml(config, given_yaml)
        update_yaml(config, cli_yaml)


def test_check_config_types_fail(tmpdir, config_dependency):
    # create temporary settings file and write yaml file
    yaml_file = Path(tmpdir) / 'settings.yaml'
    with open(yaml_file, mode='w') as f:
        yaml.dump(config_dict_fail, f)

    # create an invalid config_dependency with data from config_dict_fail
    config_setup = config_dependency(patch_path=str(yaml_file))
    config = config_setup['config']
    given_yaml = config_setup['given_yaml']
    cli_yaml = config_setup['cli_yaml']
    if given_yaml is not None:
        update_yaml(config, given_yaml)
    update_yaml(config, cli_yaml)
    with pytest.raises(KeyError):
        check_config_types(config)


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


# test the final config from parse_config with each command line option

def test_cli_yaml():
    with patch.object(sys, 'argv', cli_options[1]):
        config = parse_config()
        assert config['output_path'] == '.'
    with patch.object(sys, 'argv', cli_options[2]):
        config = parse_config()
        assert config['search_terms']['keywords'] == ['java', 'python']
    with patch.object(sys, 'argv', cli_options[3]):
        config = parse_config()
        assert config['search_terms']['region']['province'] == 'ON'
    with patch.object(sys, 'argv', cli_options[4]):
        config = parse_config()
        assert config['search_terms']['region']['city'] == 'New York'
    with patch.object(sys, 'argv', cli_options[5]):
        config = parse_config()
        assert config['search_terms']['region']['domain'] == 'com'
    with patch.object(sys, 'argv', cli_options[6]):
        config = parse_config()
        assert config['delay_config']['random'] is True
    with patch.object(sys, 'argv', cli_options[7]):
        config = parse_config()
        assert config['delay_config']['converge'] is True
    with patch.object(sys, 'argv', cli_options[8]):
        config = parse_config()
        assert config['delay_config']['delay'] == 20
    with patch.object(sys, 'argv', cli_options[9]):
        config = parse_config()
        assert config['delay_config']['min_delay'] == 10
    with patch.object(sys, 'argv', cli_options[10]):
        config = parse_config()
        assert config['delay_config']['function'] == 'linear'
    with patch.object(sys, 'argv', cli_options[11]):
        config = parse_config()
        assert config['log_level'] == log_levels['info']
    with patch.object(sys, 'argv', cli_options[12]):
        config = parse_config()
        assert config['similar'] is True
    with patch.object(sys, 'argv', cli_options[13]):
        config = parse_config()
        assert config['no_scrape'] is True
    with patch.object(sys, 'argv', cli_options[14]):
        config = parse_config()
        assert config['proxy'] == {
            'protocol': 'http',
            'ip_address': '50.193.9.202',
            'port': '53888'
        }
