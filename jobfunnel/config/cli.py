"""Configuration parsing module for CLI --> JobFunnelConfig
"""
import argparse
import logging
import os
from typing import Dict, Any, List
import yaml

from jobfunnel.config import (
    JobFunnelConfig, DelayConfig, SearchConfig, ProxyConfig)
from jobfunnel.backend.tools.tools import split_url
from jobfunnel.resources import (
    Locale, DelayAlgorithm, DEFAULT_OUTPUT_DIRECTORY, DEFAULT_CACHE_DIRECTORY,
)


def parse_cli():
    """Parse the command line arguments into an argv with defaults
    """
    parser = argparse.ArgumentParser('Job Search CLI')

    # path args
    parser.add_argument(
        '-s',
        dest='settings_yaml_file',
        type=str,
        help='Path to a settings YAML file containing your job search info. '
             'Pass an existing YAML file path to continue a search '
             'by scraping new jobs and updating the CSV file. '
    )

    # FIXME: make it mutually exclusive to pass -o or -mscv/-bl/-cache
    parser.add_argument(
        '-o',
        dest='job_search_results_folder',
        default=DEFAULT_OUTPUT_DIRECTORY,
        help='Directory where the job search results will be stored. '
             'Pass an existing search results folder to continue a search '
             'by scraping new jobs and updating the CSV file. '
             'Note that you should use seperate folders per-job-search! '
             'Folder contents: <folder>/data/.cache/, <folder>/master_list.csv.'
             ' These folders and associated files will be created if not found.'
             f' Defaults to: {DEFAULT_OUTPUT_DIRECTORY}'
    )

    # parser.add_argument(
    #     '-cache',
    #     dest='cache_folder',
    #     default=DEFAULT_CACHE_DIRECTORY,
    #     help='Directory where cached scrape data will be stored. defaults to '
    #          + DEFAULT_CACHE_DIRECTORY
    # )

    # parser.add_argument(
    #     '-bl',
    #     dest='block-list-file',
    #     nargs='*',
    #     help='JSON file of jobs you want to omit from your job search '
    #          '(usually this is in the output of previous jobfunnel results).'
    # )

    # parser.add_argument(
    #     '-mcsv',
    #     dest='master_csv_file',
    #     nargs='*',
    #     help='Path to a master CSV file containing your search results'
    # )

    # Search terms
    parser.add_argument(
        '-k',
        dest='search_keywords',
        nargs='+',
        default=['Python'],
        help='List of job-search keywords. (i.e. Engineer, AI).'
    )

    parser.add_argument(
        '-l',
        dest='locale',
        default=Locale.CANADA_ENGLISH,
        choices=[l.name for l in Locale],
        help='Global location and language to use to scrape the job provider'
             ' website. (i.e. CANADA_ENGLISH --> indeed --> indeed.ca)'
    )

    parser.add_argument(
        '-p',
        dest='province_or_state',
        default='ON',  # TODO: we should use a Local object of some sort.
        type=str,
        help='Province/state value for your job-search region. NOTE: format '
             'is job-provider-specific.'
    )

    parser.add_argument(
        '-c',
        dest='city',
        default='Waterloo',
        type=str,
        help='City/town value for job-search region.'
    )

    parser.add_argument(
        '-max-age',
        type=int,
        help='The maximum number of days-old a job can be. (i.e pass 30 to '
        'filter out jobs older than a month).'
    )

    # Functionality
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['critical', 'error', 'warning', 'info', 'debug', 'notset'],
        help='Type of logging information shown on the terminal.'
    )

    parser.add_argument(
        '--recover',
        action='store_true',
        help='Reconstruct a new master CSV file from all available cache files.'
    )

    parser.add_argument(
        '--save-duplicates',
        action='store_true',
        help='Save duplicate job key_ids into file.'
    )

    # # Proxy stuff move to subparser.
    # # FIXME missing stuff here
    # parser.add_argument(
    #     '--proxy',
    #     type=str,
    #     help='Proxy address (URL).'
    # )

    # # Delay stuff
    # # TODO: move delay args into a subparser for improved -h clarity
    # parser.add_argument(
    #     '--random-delay',
    #     action='store_true',
    #     help='Turn on random delaying for certain get requests.'
    # )

    # parser.add_argument(
    #     '--converging-delay',
    #     action='store_true',
    #     help='Use converging random delay for certain get requests.'
    # )

    # parser.add_argument(
    #     '-delay-duration',
    #     type=float,
    #     help='Set delay seconds for certain get requests.'
    # )

    # parser.add_argument(
    #     '-delay-min',
    #     type=float,
    #     help='Set lower bound value for delay for certain get requests.'
    # )

    # parser.add_argument(
    #     '-delay-algorithm',
    #     choices=[a.name for a in DelayAlgorithm],
    #     help='Select a function to calculate delay times with.'
    # )


    return parser.parse_args()


def config_builder(args: argparse.Namespace) -> JobFunnelConfig:
    """Parse the JobFunnel configuration settings.
    """
    #if args.yaml
    import pdb; pdb.set_trace()
    # # parse the settings file for the line arguments
    # given_yaml = None
    # given_yaml_path = None
    # if cli.settings is not None:
    #     given_yaml_path = os.path.dirname(cli.settings)
    #     given_yaml = yaml.safe_load(open(cli.settings, 'r'))

    # # combine default, given and argument yamls into one. Note that we update
    # # the values of the default_yaml, so we use this for the rest of the file.
    # # We could make a deep copy if necessary.
    # config = default_yaml
    # if given_yaml is not None:
    #     update_yaml(config, given_yaml)
    # update_yaml(config, cli_yaml)
    # # check if the config has valid attribute types
    # check_config_types(config)

    # # create output path and corresponding (children) data paths
    # # I feel like this is not in line with the rest of the file's philosophy
    # if cli.output_path is not None:
    #     output_path = cli.output_path
    # elif given_yaml_path is not None:
    #     output_path = os.path.join(given_yaml_path, given_yaml['output_path'])
    # else:
    #     output_path = default_yaml['output_path']

    # # define paths and normalise
    # config['data_path'] = os.path.join(output_path, 'data')
    # config['master_list_path'] = os.path.join(output_path, 'master_list.csv')
    # config['duplicate_list_path'] = os.path.join(
    #     output_path, 'duplicate_list.csv')
    # config['filter_list_path'] = os.path.join(
    #     config['data_path'], 'filter_list.json')
    # config['log_path'] = os.path.join(config['data_path'], 'jobfunnel.log')

    # # normalize paths
    # for p in ['data_path', 'master_list_path', 'duplicate_list_path',
    #           'log_path', 'filter_list_path']:
    #     config[p] = os.path.normpath(config[p])

    # # lower provider and delay function
    # for i, p in enumerate(config['providers']):
    #     config['providers'][i] = p.lower()
    # config['delay_config']['function'] = \
    #     config['delay_config']['function'].lower()

    # # parse the log level
    # config['log_level'] = LOG_LEVELS_MAP[config['log_level']]

    # # parse the locale into Locale (must be upper case and match enum def name)
    # for locale in Locale:
    #     if locale.name == config['locale']:
    #         config['locale'] = locale

    # # check if proxy and max_listing_days have not been set yet (optional)
    # if 'proxy' not in config:
    #     config['proxy'] = None
    # if 'max_listing_days' not in config:
    #     config['max_listing_days'] = None

    # return config

    search_cfg = SearchConfig(
        keywords=config['search_terms']['keywords'],
        province_or_state=config['search_terms']['region']['province_or_state'],
        city=config['search_terms']['region']['city'],
        distance_radius_km=config['search_terms']['region']['radius'],
        return_similar_results=False,
        max_listing_days=config['max_listing_days'],
        blocked_company_names=config['company_block_list'],
    )

    delay_cfg = DelayConfig(
        duration=config['delay_config']['delay'],
        min_delay=config['delay_config']['min_delay'],
        function_name=config['delay_config']['function'],
        random=config['delay_config']['random'],
        converge=config['delay_config']['converge'],
    )

    if config['proxy']:
        proxy_cfg = ProxyConfig(
            protocol=config['proxy']['protocol'],
            ip_address=config['proxy']['ip_address'],
            port=config['proxy']['port'],
        )
    else:
        proxy_cfg = None

    funnel_cfg = JobFunnelConfig(
        master_csv_file=config['master_list_path'],
        user_block_list_file=config['filter_list_path'],
        duplicates_list_file=config['duplicate_list_path'],
        cache_folder=config['data_path'],
        search_terms=search_cfg,
        provider_names=config['providers'],
        locale=config['locale'],
        log_file=config['log_path'],
        log_level=config['log_level'],
        no_scrape=config['no_scrape'],
        delay_config=delay_cfg,
        proxy_config=proxy_cfg,
    )
    return funnel_cfg
