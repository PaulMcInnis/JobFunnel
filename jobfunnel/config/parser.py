"""Configuration parsing module.

"""
import argparse
import logging
import os
import yaml

from argparse import RawTextHelpFormatter
from termcolor import colored
from colorama import init as colorama_init

from .valid_options import CONFIG_TYPES
from ..tools.tools import split_url

DESCRIPTION = ('CLI options take precedence over settings in the yaml file'
               'empty arguments are replaced by settings in the default yaml'
               'file')

LOG_LEVELS = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
    'notset': logging.NOTSET
    }

CHOICES = {
    'log_level': ['critical', 'error', 'warning', 'info', 'debug', 'notset'],
    'function': ['constant', 'linear', 'sigmoid']
    }

COLOR = 'green'
ATTRS = ['bold']

choices_str = colored('\nchoices:', COLOR, attrs=ATTRS)

class ConfigError(ValueError):
    def __init__(self, arg):
        self.strerror = f"ConfigError: '{arg}' has an invalid value"
        self.args = {arg}


def parse_cli():
    """ Parse the command line arguments.

    """
    colorama_init()
    parser = argparse.ArgumentParser(
        description=DESCRIPTION,
        formatter_class=RawTextHelpFormatter
    )

    parser.add_argument('-s',
                        '--settings',
                        dest='settings',
                        type=str,
                        required=False,
                        help='path to the yaml settings file',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-o',
                        '--output_path',
                        dest='output_path',
                        type=str,
                        action='store',
                        required=False,
                        help='directory where the search results will be '
                             'stored',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-kw',
                        '--keywords',
                        dest='keywords',
                        nargs='*',
                        required=False,
                        help='list of keywords to use in the job search',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-p',
                        '--province',
                        dest='province',
                        type=str,
                        required=False,
                        help='province value for a region ('
                             'takes precedence over state)',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-st',
                        '--state',
                        dest='state',
                        type=str,
                        required=False,
                        help='state value for a region',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-ci',
                        '--city',
                        dest='city',
                        type=str,
                        required=False,
                        help='city value for a region',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-d',
                        '--domain',
                        dest='domain',
                        type=str,
                        required=False,
                        help='domain value for a region',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-r',
                        '--random',
                        dest='random',
                        action='store_true',
                        required=False,
                        default=None,
                        help='pass to turn on random delaying')

    parser.add_argument('-c',
                        '--coverage',
                        dest='converge',
                        action='store_true',
                        required=False,
                        default=None,
                        help='pass to use a converging random delay')

    parser.add_argument('-dl',
                        '--delay',
                        dest='delay',
                        type=float,
                        required=False,
                        help='set the maximum delay in seconds for scrapes',
                        metavar=colored(float.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-md',
                        '--min_delay',
                        dest='min_delay',
                        type=float,
                        required=False,
                        help='set the minimum delay in seconds for scraper',
                        metavar=colored(float.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-f',
                        '--fun',
                        dest='function',
                        type=str,
                        required=False,
                        default=None,
                        choices=CHOICES['function'],
                        help='select a function to calculate delay times '
                             '{} {}'.format(choices_str, CHOICES['function']),
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-ll',
                        '--log_level',
                        dest='log_level',
                        type=str,
                        required=False,
                        default=None,
                        choices=CHOICES['log_level'],
                        help='type of logging information shown in the '
                             'terminal '
                             '{} {}'.format(choices_str, CHOICES['log_level']),
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-si',
                        '--similar',
                        dest='similar',
                        action='store_true',
                        default=None,
                        help='pass to get similar job listings')

    parser.add_argument('-ns',
                        '--no_scrape',
                        dest='no_scrape',
                        action='store_true',
                        default=None,
                        help='pass to skip web-scraping and load a previously'
                             'saved daily scrape pickle')

    parser.add_argument('-px',
                        '--proxy',
                        dest='proxy',
                        type=str,
                        required=False,
                        default=None,
                        help='proxy address',
                        metavar=colored(str.__name__, COLOR, attrs=ATTRS))

    parser.add_argument('-rv',
                        '--recover',
                        dest='recover',
                        action='store_true',
                        default=None,
                        help='pass to recover the master-list file by accessing '
                             'all historic scrape pickles')

    parser.add_argument('-sd',
                        '--save_dup',
                        dest='save_duplicates',
                        action='store_true',
                        required=False,
                        default=None,
                        help='pass to save duplicates popped by tf_idf filter '
                             'to file')

    return parser.parse_args()


def cli_to_yaml(cli):
    """ Put program arguments into dictionary in same style as configuration
        yaml.

    """
    yaml = {
        'output_path': cli.output_path,
        'search_terms': {
            'region': {
                'province': cli.province,
                'state': cli.state,
                'city': cli.city,
                'domain': cli.domain
            },
            'keywords': cli.keywords
        },
        'log_level': cli.log_level,
        'similar': cli.similar,
        'no_scrape': cli.no_scrape,
        'recover': cli.recover,
        'save_duplicates': cli.save_duplicates,
        'delay_config': {
            'function': cli.function,
            'delay': cli.delay,
            'min_delay': cli.min_delay,
            'random': cli.random,
            'converge': cli.converge
        }
    }

    if cli.proxy is not None:
        yaml['proxy'] = split_url(cli.proxy)

    return yaml


def update_yaml(config, new_yaml):
    """ Update fields of current yaml with new yaml.

    """
    for k, v in new_yaml.items():
        # if v is a dict we need to dive deeper...
        if type(v) is dict:
            update_yaml(config[k], v)
        else:
            if v is not None:
                config[k] = v


def recursive_check_config_types(config, types):
    """ Recursively check type of setting vars.

    """
    for k, v in config.items():
        # if type is dict than we have to recursively handle this
        if type(v) is dict:
            yield from recursive_check_config_types(v, types[k])
        else:
            yield (k, type(v) in types[k])


def check_config_types(config):
    """ Check if no settings have a wrong type and if we do not have unsupported
    options.

    """
    # Get a dictionary of all types and boolean if it's the right type
    types_check = recursive_check_config_types(config, CONFIG_TYPES)

    # Select all wrong types and throw error when there is such a value
    wrong_types = [k for k, v in types_check if v is False]
    if len(wrong_types) > 0:
        raise ConfigError(', '.join(wrong_types))


def parse_config():
    """ Parse the JobFunnel configuration settings.

    """
    # find the jobfunnel root dir
    jobfunnel_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..'))

    # load the default settings
    default_yaml_path = os.path.join(jobfunnel_path, 'config/settings.yaml')
    default_yaml = yaml.safe_load(open(default_yaml_path, 'r'))

    # parse the command line arguments
    cli = parse_cli()
    cli_yaml = cli_to_yaml(cli)

    # parse the settings file for the line arguments
    given_yaml = None
    given_yaml_path = None
    if cli.settings is not None:
        given_yaml_path = os.path.dirname(cli.settings)
        given_yaml = yaml.safe_load(open(cli.settings, 'r'))

    # combine default, given and argument yamls into one. Note that we update
    # the values of the default_yaml, so we use this for the rest of the file.
    # We could make a deep copy if necessary.
    config = default_yaml
    if given_yaml is not None:
        update_yaml(config, given_yaml)
    update_yaml(config, cli_yaml)

    # check if the config has valid attribute types
    check_config_types(config)

    # create output path and corresponding (children) data paths
    # I feel like this is not in line with the rest of the file's philosophy
    if cli.output_path is not None:
        output_path = cli.output_path
    elif given_yaml_path is not None:
        output_path = os.path.join(given_yaml_path, given_yaml['output_path'])
    else:
        output_path = default_yaml['output_path']

    # define paths and normalise
    config['data_path'] = os.path.join(output_path, 'data')
    config['master_list_path'] = os.path.join(output_path, 'master_list.csv')
    config['duplicate_list_path'] = os.path.join(
        output_path, 'duplicate_list.csv')
    config['filter_list_path'] = os.path.join(
        config['data_path'], 'filter_list.json')
    config['log_path'] = os.path.join(config['data_path'], 'jobfunnel.log')

    # normalize paths
    for p in ['data_path', 'master_list_path', 'duplicate_list_path',
              'log_path', 'filter_list_path']:
        config[p] = os.path.normpath(config[p])

    # lower provider and delay function
    for i, p in enumerate(config['providers']):
        config['providers'][i] = p.lower()
    config['delay_config']['function'] = \
        config['delay_config']['function'].lower()

    # parse the log level
    config['log_level'] = LOG_LEVELS[config['log_level']]

    # check if proxy has not been set yet (optional)
    if 'proxy' not in config:
        config['proxy'] = None

    return config
