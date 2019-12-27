"""Configuration parsing module.

"""
import argparse
import logging
import os
import yaml

log_levels = {'critical': logging.CRITICAL, 'error': logging.ERROR,
              'warning': logging.WARNING, 'info': logging.INFO,
              'debug': logging.DEBUG, 'notset': logging.NOTSET}


def _parse_cli():
    """Parse the command line arguments.

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

    parser.add_argument('--recover',
                        dest='recover',
                        action='store_true',
                        default=False,
                        help='recover master-list by accessing all historic '
                             'scrapes pickles')

    return parser.parse_args()


def parse_config():
    """Parse the JobFunnel configuration settings.

    """
    # find the jobfunnel root dir
    jobfunnel_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), '..'))

    # load the default settings
    default_yaml_path = os.path.join(jobfunnel_path, 'config/settings.yaml')
    default_yaml = yaml.safe_load(open(default_yaml_path, 'r'))

    # parse the command line arguments
    cli = _parse_cli()

    # parse the settings file for the line arguments
    given_yaml = None
    given_yaml_path = None
    if cli.settings is not None:
        given_yaml_path = os.path.dirname(cli.settings)
        given_yaml = yaml.safe_load(open(cli.settings, 'r'))

    # prepare the configuration dictionary
    config = {}

    # parse the data path
    config['data_path'] = os.path.join(default_yaml['output_path'], 'data')
    config['master_list_path'] = os.path.join(
        default_yaml['output_path'], 'master_list.csv')
    if given_yaml_path is not None:
        config['data_path'] = os.path.join(
            given_yaml_path, given_yaml['output_path'], 'data')
        config['master_list_path'] = os.path.join(
            given_yaml_path, given_yaml['output_path'], 'master_list.csv')
    if cli.output_path is not None:
        config['data_path'] = os.path.join(cli.output_path, 'data')
        config['master_list_path'] = os.path.join(
            cli.output_path, 'master_list.csv')

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

    # define the log path
    config['log_path'] = os.path.join(config['data_path'], 'jobfunnel.log')

    # define the filter list path
    config['filter_list_path'] = os.path.join(
        config['data_path'], 'filter_list.json')

    # normalize paths
    for p in ['data_path', 'master_list_path', 'log_path', 'filter_list_path']:
        config[p] = os.path.normpath(config[p])

    return config
