"""Configuration parsing module for CLI --> JobFunnelConfig
"""
import argparse
import logging
import os
from typing import Dict, Any, List
import yaml

from jobfunnel.config import (
    JobFunnelConfig, DelayConfig, SearchConfig, ProxyConfig, SettingsValidator)
from jobfunnel.backend.tools.tools import split_url
from jobfunnel.resources import (
    Locale, DelayAlgorithm, LOG_LEVEL_NAMES, Provider)
from jobfunnel.resources.defaults import *


PROVIDER_NAMES = [p.name for p in DEFAULT_PROVIDERS]


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
             'by scraping new jobs and updating the CSV file. CLI args will '
             'overwrite any settings in YAML.'
    )

    # This arg is problematic because you can't pass it and the
    # paths to the files directly.
    parser.add_argument(
        '-o',
        dest='output_folder',
        default=DEFAULT_OUTPUT_DIRECTORY,
        help='Directory where the job search results will be stored. '
             'Pass an existing search results folder to continue a search '
             'by scraping new jobs and updating the CSV file. '
             'Note that you should use seperate folders per-job-search! '
             'Folder contents: <folder>/data/.cache/, <folder>/master_list.csv.'
             ' These folders and associated files will be created if not found,'
             ' or if -cache, -blf -dl, and -csv paths are not passed as args.'
             f' Defaults to: {DEFAULT_OUTPUT_DIRECTORY}'
    )

    parser.add_argument(
        '-csv',
        dest='master_csv_file',
        default=DEFAULT_MASTER_CSV_FILE,
        nargs='*',
        help='Path to a master CSV file containing your search results. '
             f'Defaults to {DEFAULT_MASTER_CSV_FILE}'
    )

    parser.add_argument(
        '-cache',
        dest='cache_folder',
        default=DEFAULT_CACHE_DIRECTORY,
        help='Directory where cached scrape data will be stored. '
             f'Defaults to {DEFAULT_CACHE_DIRECTORY}'
    )

    parser.add_argument(
        '-blf',
        dest='block_list_file',
        nargs='*',
        default=DEFAULT_BLOCK_LIST_FILE,
        help='JSON file of jobs you want to omit from your job search '
             '(usually this is in the output of previous jobfunnel results). '
             f'Defaults to: {DEFAULT_BLOCK_LIST_FILE}'
    )

    parser.add_argument(
        '-lf',
        dest='log_file',
        type=str,
        default=DEFAULT_LOG_FILE,
        help='path to logging file.'
    )

    parser.add_argument(
        '-dl',
        dest='duplicates_list_file',
        nargs='*',
        default=DEFAULT_DUPLICATES_FILE,
        help='JSON file of jobs which have been detected to be duplicates of '
             'existing jobs (usually this is in the output of previous '
             f'jobfunnel results). Defaults to: {DEFAULT_DUPLICATES_FILE}'
    )

    parser.add_argument(
        '-cbl',
        dest='search_company_block_list',
        nargs='+',
        default=DEFAULT_COMPANY_BLOCK_LIST,
        help='List of company names to omit from all search results.'
    )

    # Search terms
    parser.add_argument(
        '-p',
        dest='search_providers',
        choices=PROVIDER_NAMES,
        default=PROVIDER_NAMES,
        help='List of job-search providers. (i.e. indeed, monster, glassdoor).'
    )

    parser.add_argument(
        '-k',
        dest='search_keywords',
        nargs='+',
        default=DEFAULT_SEARCH_KEYWORDS,
        help='List of job-search keywords. (i.e. Engineer, AI).'
    )

    parser.add_argument(
        '-l',
        dest='search_locale',
        default=DEFAULT_LOCALE.name,
        choices=[l.name for l in Locale],
        help='Global location and language to use to scrape the job provider'
             ' website. (i.e. CANADA_ENGLISH --> indeed --> indeed.ca)'
    )

    parser.add_argument(
        '-ps',
        dest='search_region_province_or_state',
        default=DEFAULT_PROVINCE,
        type=str,
        help='Province/state value for your job-search region. NOTE: format '
             'is job-provider-specific.'
    )

    parser.add_argument(
        '-c',
        dest='search_region_city',
        default=DEFAULT_CITY,
        type=str,
        help='City/town value for job-search region.'
    )

    parser.add_argument(
        '-r',
        dest='search_region_radius',
        type=int,
        default=DEFAULT_SEARCH_RADIUS_KM,
        help='The maximum distance a job should be from the specified city.'
    )

    parser.add_argument(
        '-max-listing-age',
        dest='search_max_listing_days',
        type=int,
        default=DEFAULT_MAX_LISTING_DAYS,
        help='The maximum number of days-old a job can be. (i.e pass 30 to '
        'filter out jobs older than a month).'
    )

    parser.add_argument(
        '--similar-results',
        action='store_true',
        help='Return \'similar\' results from search query (only for Indeed).'
    )

    # Functionality
    parser.add_argument(
        '--log-level',
        type=str,
        default=DEFAULT_LOG_LEVEL_NAME,
        choices=LOG_LEVEL_NAMES,
        help='Type of logging information shown on the terminal.'
    )

    parser.add_argument(
        '--recover',
        dest='recover_from_cache',
        action='store_true',
        help='Reconstruct a new master CSV file from all available cache files.'
             'WARNING: this will replace all the statuses/etc in your master '
             'CSV, it is intended for starting fresh / recovering from a bad '
             'state.'
    )

    parser.add_argument(
        '--save-duplicates',
        action='store_true',
        help='Save duplicate job key_ids into file.'
    )

    parser.add_argument(
        '--no-scrape',
        action='store_true',
        help='Do not make any get requests, and attempt to load from cache.'
    )

    # Proxy stuff
    # TODO: subparser.
    parser.add_argument(
        '-protocol',
        dest='proxy_protocol',
        type=str,
        help='Proxy protocol.'
    )
    parser.add_argument(
        '-ip',
        dest='proxy_ip',
        type=str,
        help='Proxy IP (V4) address.'
    )
    parser.add_argument(
        '-port',
        dest='proxy_port',
        type=str,
        help='Proxy port address.'
    )

    # Delay stuff
    # TODO: move delay args into a subparser for improved -h clarity
    parser.add_argument(
        '--delay-random',
        dest='delay_random',
        action='store_true',
        help='Turn on random delaying for certain get requests.'
    )

    parser.add_argument(
        '--delay-converging',
        dest='delay_converging',
        action='store_true',
        help='Use converging random delay for certain get requests.'
    )

    parser.add_argument(
        '-delay-max',
        dest='delay_max_duration',
        default=DEFAULT_DELAY_MAX_DURATION,
        type=float,
        help='Set delay seconds for certain get requests.'
    )

    parser.add_argument(
        '-delay-min',
        dest='delay_min_duration',
        default=DEFAULT_DELAY_MIN_DURATION,
        type=float,
        help='Set lower bound value for delay for certain get requests.'
    )

    parser.add_argument(
        '-delay-algorithm',
        default=DEFAULT_DELAY_ALGORITHM.name,
        choices=[a.name for a in DelayAlgorithm],
        help='Select a function to calculate delay times with.'
    )

    return parser.parse_args()


def config_builder(args: argparse.Namespace) -> JobFunnelConfig:
    """Parse the JobFunnel configuration settings into a JobFunnelConfig.

        args [argparse.Namespace]: cli arguments from argparser
    """
    # Load config dict from the YAML (may be default)
    args_dict = vars(args)
    if args_dict.pop('settings_yaml_file'):
        config = yaml.load(
            open(args.settings_yaml_file, 'r'), Loader=yaml.FullLoader
        )
    else:
        config = DEFAULT_CONFIG

    # Are we recovering? NOTE: this arg is not part of yaml like settings path
    recover_from_cache = args_dict.pop('recover_from_cache')

    # Ensure that if user provided output folder that the other paths aren't
    if (args_dict['output_folder'] != DEFAULT_OUTPUT_DIRECTORY and (
            args_dict['master_csv_file'] != DEFAULT_MASTER_CSV_FILE
            or args_dict['block_list_file'] != DEFAULT_BLOCK_LIST_FILE
            or args_dict['duplicates_list_file'] != DEFAULT_DUPLICATES_FILE
            or args_dict['cache_folder'] != DEFAULT_CACHE_DIRECTORY)):

            raise ValueError(
                "When providing output_folder, do not also provide -csv, -blf"
                ", -dlf, or -cache, as these are defined by the output folder."
                " If specifying file paths you must pass all the arguments and"
                " not pass -o."
            )

    # Inject any modified attributs only if they override our config/defaults
    # TODO less messy way to do this?
    output_folder = args_dict.pop('output_folder')
    for key, value in args_dict.items():
        if key in config and config[key] != value:
            config[key] = value
            continue
        if 'search_region' in key:
            sub_sub_cfg_key = key.split('search_region_')[1]
            if config['search']['region'][sub_sub_cfg_key] != value:
                config['search']['region'][sub_sub_cfg_key] = value
            continue
        for sub_cfg_name in ['search', 'delay', 'proxy']:
            if sub_cfg_name in key:
                sub_cfg_key = key.split(f'{sub_cfg_name}_')[1]
                if config[sub_cfg_name][sub_cfg_key] != value:
                    config[sub_cfg_name][sub_cfg_key] = value
                continue

    # Create any folders that we need
    if output_folder:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        if not os.path.exists(args_dict['cache_folder']):
            os.makedirs(args_dict['cache_folder'])

    # Validate the config we have built
    if not SettingsValidator.validate(config):
        # TODO: some way to print allowed values in error msg?
        raise ValueError(
            f"Invalid Config settings yaml:\n{SettingsValidator.errors}"
        )

    # Build JobFunnelConfig
    search_cfg = SearchConfig(
        keywords=config['search']['keywords'],
        province_or_state=config['search']['region']['province_or_state'],
        city=config['search']['region']['city'],
        distance_radius=config['search']['region']['radius'],
        return_similar_results=config['search']['similar_results'],
        max_listing_days=config['search']['max_listing_days'],
        blocked_company_names=config['search']['company_block_list'],
        locale=Locale[config['search']['locale']],
        providers=[Provider[p] for p in config['search']['providers']],
    )

    delay_cfg = DelayConfig(
        max_duration=config['delay']['max_duration'],
        min_duration=config['delay']['min_duration'],
        algorithm=DelayAlgorithm[config['delay']['algorithm']],
        random=config['delay']['random'],
        converge=config['delay']['converging'],
    )

    if config['proxy']['ip']:
        proxy_cfg = ProxyConfig(
            protocol=config['proxy']['protocol'],
            ip_address=config['proxy']['ip'],
            port=config['proxy']['port'],
        )
    else:
        proxy_cfg = None

    funnel_cfg = JobFunnelConfig(
        master_csv_file=config['master_csv_file'],
        user_block_list_file=config['block_list_file'],
        duplicates_list_file=config['duplicates_list_file'],
        cache_folder=config['cache_folder'],
        log_file=config['log_file'],
        log_level=config['log_level'],
        no_scrape=config['no_scrape'],
        # bs4_parser=config['bs4_parser'], # TODO: impl. cli/cfg when needed.
        recover_from_cache=recover_from_cache,  # NOTE: this isn't in YAML
        search_config=search_cfg,
        delay_config=delay_cfg,
        proxy_config=proxy_cfg,
    )

    # Validate funnel config as well (checks some stuff Cerberus doesn't rn)
    funnel_cfg.validate()

    return funnel_cfg
