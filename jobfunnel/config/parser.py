"""Configuration parsing module.

"""
import argparse
import logging
import os
import re
import yaml

from .valid_options import PROVIDERS, DOMAINS

log_levels = {'critical': logging.CRITICAL, 'error': logging.ERROR,
              'warning': logging.WARNING, 'info': logging.INFO,
              'debug': logging.DEBUG, 'notset': logging.NOTSET}


class ConfigError(ValueError):
     def __init__(self, arg):
         self.strerror = f"ConfigError: '{arg}' has an invalid value"
         self.args = {arg}


def parse_cli():
    """ Parse the command line arguments.

    """
    parser = argparse.ArgumentParser(
        'CLI options take precedence over settings in the yaml file'
        'empty arguments are replaced by settings in the default yaml file')

    parser.add_argument('-s',
                        dest='settings',
                        type=str,
                        required=False,
                        help='path to the yaml settings file')

    parser.add_argument('-o',
                        dest='output_path',
                        action='store',
                        required=False,
                        help='directory where the search results will be '
                             'stored')

    parser.add_argument('-kw',
                        dest='keywords',
                        nargs='*',
                        required=False,
                        help='list of keywords to use in the job search. ('
                             'i.e. Engineer, AI)')

    parser.add_argument('-r',
                        dest='random',
                        action='store_true',
                        required=False,
                        default=None,
                        help='turn on random delaying')

    parser.add_argument('-c',
                        dest='converge',
                        action='store_true',
                        required=False,
                        default=None,
                        help='use converging random delay')

    parser.add_argument('-d',
                        dest='delay',
                        type=float,
                        required=False,
                        help='set delay seconds for scrapes.')

    parser.add_argument('-md',
                        dest='min_delay',
                        type=float,
                        required=False,
                        help='set lower bound value for scraper')

    parser.add_argument('--fun',
                        dest='function',
                        type=str,
                        required=False,
                        default=None,
                        choices=['constant', 'linear', 'sigmoid'],
                        help='Select a function to calculate delay times with')

    parser.add_argument('--log_level',
                        dest='log_level',
                        type=str,
                        required=False,
                        default=None,
                        choices=['critical', 'error', 'warning', 'info',
                                 'debug', 'notset'],
                        help='Type of logging information shown on the '
                             'terminal.')

    parser.add_argument('--similar',
                        dest='similar',
                        action='store_true',
                        default=False,
                        help='pass to get \'similar\' job listings')

    parser.add_argument('--no_scrape',
                        dest='no_scrape',
                        action='store_true',
                        default=False,
                        help='skip web-scraping and load a previously saved '
                             'daily scrape pickle')

    parser.add_argument('--no_delay',
                        dest='set_delay',
                        action='store_false',
                        required=False,
                        default=None,
                        help='Turn random delay off, not a recommended action')

    parser.add_argument('--recover',
                        dest='recover',
                        action='store_true',
                        default=False,
                        help='recover master-list by accessing all historic '
                             'scrapes pickles')

    parser.add_argument('--save_dup',
                        dest='save_duplicates',
                        action='store_true',
                        required=False,
                        default=None,
                        help='save duplicates popped by tf_idf filter to file')

    return parser.parse_args()


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

    # parse the settings file for the line arguments
    given_yaml = None
    given_yaml_path = None
    if cli.settings is not None:
        given_yaml_path = os.path.dirname(cli.settings)
        given_yaml = yaml.safe_load(open(cli.settings, 'r'))

    # prepare the configuration dictionary
    config = {}

    # parse the output path
    output_path = default_yaml['output_path']
    if given_yaml_path is not None:
        output_path = os.path.join(given_yaml_path, given_yaml['output_path'])
    if cli.output_path is not None:
        output_path = cli.output_path
    
    config['data_path'] = os.path.join(output_path, 'data')
    config['master_list_path'] = os.path.join(output_path, 'master_list.csv')
    config['duplicate_list_path'] = os.path.join(output_path, 'duplicate_list.csv')

    # parse the provider list
    config['providers'] = default_yaml['providers']
    if given_yaml_path is not None:
        config['providers'] = given_yaml['providers']
    for i, p in enumerate(config['providers']):
        config['providers'][i] = p.lower()

    # parse the search terms
    config['search_terms'] = default_yaml['search_terms']
    if given_yaml_path is not None:
        config['search_terms'] = given_yaml['search_terms']
    if cli.keywords is not None:
        config['search_terms']['keywords'] = cli.keywords

    # search term state is inserted as province if province does not already exist
    if 'state' in config['search_terms']['region']:
        if (config['search_terms']['region']['state'] is not None) and \
                (config['search_terms']['region']['province'] is None):
            config['search_terms']['region']['province'] = \
                config['search_terms']['region']['state']

    # parse the blacklist
    config['black_list'] = default_yaml['black_list']
    if given_yaml_path is not None:
        config['black_list'] = given_yaml['black_list']

    # parse the similar option
    config['similar'] = cli.similar

    # parse the no_scrape option
    config['no_scrape'] = cli.no_scrape

    # parse the recovery option
    config['recover'] = cli.recover

    # parse the log level
    config['log_level'] = log_levels[default_yaml['log_level']]
    if given_yaml_path is not None:
        config['log_level'] = log_levels[given_yaml['log_level']]
    if cli.log_level is not None:
        config['log_level'] = log_levels[cli.log_level]

    # parse save_duplicates option
    config['save_duplicates'] = default_yaml['save_duplicates']
    if given_yaml_path is not None:
        config['save_duplicates'] = given_yaml['save_duplicates']
    if cli.save_duplicates is not None:
        config['save_duplicates'] = cli.save_duplicates

    # define the log path
    config['log_path'] = os.path.join(config['data_path'], 'jobfunnel.log')

    # define the filter list path
    config['filter_list_path'] = os.path.join(
        config['data_path'], 'filter_list.json')

    # set delaying
    config['set_delay'] = default_yaml['set_delay']
    if given_yaml_path is not None:
        config['set_delay'] = given_yaml['set_delay']
    if cli.set_delay is not None:
        config['set_delay'] = cli.set_delay

    # parse options for delaying if turned on
    if config['set_delay']:
        config['delay_config'] = default_yaml['delay_config']
        if given_yaml_path is not None:
            config['delay_config'] = given_yaml['delay_config']

        # cli options for delaying configuration
        if cli.function is not None:
            config['delay_config']['function'] = cli.function
        if cli.delay is not None:
            config['delay_config']['delay'] = cli.delay
        if cli.min_delay is not None:
            config['delay_config']['min_delay'] = cli.min_delay
        if cli.random is not None:
            config['delay_config']['random'] = cli.random
            if cli.converge is not None:
                config['delay_config']['converge'] = cli.converge

        # converts function name to lower case in config
        config['delay_config']['function'] = \
            config['delay_config']['function'].lower()
    else:
        config['delay_config'] = None
    
    # normalize paths
    for p in ['data_path', 'master_list_path', 'duplicate_list_path',
              'log_path', 'filter_list_path']:
        config[p] = os.path.normpath(config[p])

    return config


def check_region(region):
    """ Check if the region settings are valid

    """
    # only allow supported domains
    if not region['domain'] in DOMAINS:
        raise ConfigError('domain')
    
    # city should always be provided in the region settings (for now)
    if 'city' not in region:
        raise ConfigError('city')
    
    # north american jobs should have a province/state provided
    if region['domain'] in ['com', 'ca'] and 'province' not in region:
        raise ConfigError('province')

    if 'radius' not in region:
        raise ConfigError('radius')
    elif type(region['radius']) is not int:
        raise ConfigError('radius')


def check_config(config):
    """ Check whether the config is a valid configuration. 
    
    Some options are already checked at the command-line tool, e.g., loggging.
    """
    # check if paths are valid
    check_paths = {
        'data_path': r'data$',
        'master_list_path': r'master_list\.csv$',
        'duplicate_list_path': r'duplicate_list\.csv$',
        'log_path': r'data\/jobfunnel.log$',
        'filter_list_path': r'data\/filter_list\.json$',
    }

    for path, pattern in check_paths.items():
        if not re.search(pattern, config[path]):
            raise ConfigError(path)

    # check if the provider list only consists of supported providers
    if not set(config['providers']).issubset(PROVIDERS):
        raise ConfigError('providers')

    # check validity of region settings
    check_region(config['search_terms']['region'])

    # search terms should be a list
    if type(config['search_terms']['keywords']) is not list:
        raise ConfigError('keywords')
    
    # idem for blacklist although I think it's better if we allow black_list
    # to be None
    if type(config['black_list']) is not list:
        raise ConfigError('black_list')
    
    # save_duplicates should either be true or false
    if type(config['save_duplicates']) is not bool:
        raise ConfigError('save_duplicates')

    if type(config['set_delay']) is not bool:
        raise ConfigError('set_delay')
