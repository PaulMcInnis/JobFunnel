"""Configuration parsing module for CLI --> JobFunnelConfigManager
"""
import argparse
import logging
import os
from typing import Any, Dict, List

import yaml

from jobfunnel.config import (SETTINGS_YAML_SCHEMA, DelayConfig,
                              JobFunnelConfigManager, ProxyConfig,
                              SearchConfig, SettingsValidator)
from jobfunnel.resources import (LOG_LEVEL_NAMES, DelayAlgorithm, Locale,
                                 Provider)
from jobfunnel.resources.defaults import *


def parse_cli():
    """Parse the command line arguments into an argv with defaults

    NOTE: we only provide defaults for entries that are required and have no
    default in Cerberus schema (SettingsValidator), this lets users try it out
    without having to configure anything at all.
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
        nargs='*',
        help='Path to a master CSV file containing your search results. '
             f'Defaults to {DEFAULT_MASTER_CSV_FILE}'
    )

    parser.add_argument(
        '-cache',
        dest='cache_folder',
        help='Directory where cached scrape data will be stored. '
             f'Defaults to {DEFAULT_CACHE_DIRECTORY}'
    )

    parser.add_argument(
        '-blf',
        dest='block_list_file',
        nargs='*',
        help='JSON file of jobs you want to omit from your job search '
             '(usually this is in the output of previous jobfunnel results). '
             f'Defaults to: {DEFAULT_BLOCK_LIST_FILE}'
    )

    parser.add_argument(
        '-dl',
        dest='duplicates_list_file',
        nargs='*',
        help='JSON file of jobs which have been detected to be duplicates of '
             'existing jobs (usually this is in the output of previous '
             f'jobfunnel results). Defaults to: {DEFAULT_DUPLICATES_FILE}'
    )

    parser.add_argument(
        '-lf',
        dest='log_file',
        type=str,
        help=f'path to logging file. defaults to {DEFAULT_LOG_FILE}'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default=DEFAULT_LOG_LEVEL_NAME,
        choices=LOG_LEVEL_NAMES,
        help='Type of logging information shown on the terminal.'
    )

    parser.add_argument(
        '-cbl',
        dest='search_company_block_list',
        nargs='+',
        help='List of company names to omit from all search results.'
    )

    # Search terms
    parser.add_argument(
        '-p',
        dest='search_providers',
        nargs='+',
        choices=[p.name for p in Provider],
        default=[p.name for p in DEFAULT_PROVIDERS],
        help='List of job-search providers. (i.e. indeed, monster, glassdoor).'
    )

    parser.add_argument(
        '-kw',
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
        dest='search_province_or_state',
        default=DEFAULT_PROVINCE,
        type=str,
        help='Province/state value for your job-search region. NOTE: format '
             'is job-provider-specific.'
    )

    parser.add_argument(
        '-c',
        dest='search_city',
        default=DEFAULT_CITY,
        type=str,
        help='City/town value for job-search region.'
    )

    parser.add_argument(
        '-r',
        dest='search_radius',
        type=int,
        help='The maximum distance a job should be from the specified city.'
    )

    parser.add_argument(
        '-max-listing-days',
        dest='search_max_listing_days',
        type=int,
        help='The maximum number of days-old a job can be. (i.e pass 30 to '
        'filter out jobs older than a month).'
    )

    parser.add_argument(
        '--similar-results',
        dest='search_similar_results',
        action='store_true',
        help='Return \'similar\' results from search query (only for Indeed).'
    )

    # Flags: NOTE: all the defaults for these should be False.
    parser.add_argument(
        '--recover',
        dest='do_recovery_mode',
        action='store_true',
        help='Reconstruct a new master CSV file from all available cache files.'
             'WARNING: this will replace all the statuses/etc in your master '
             'CSV, it is intended for starting fresh / recovering from a bad '
             'state.'
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
        type=float,
        help='Set delay seconds for certain get requests.'
    )

    parser.add_argument(
        '-delay-min',
        dest='delay_min_duration',
        type=float,
        help='Set lower bound value for delay for certain get requests.'
    )

    parser.add_argument(
        '-delay-algorithm',
        choices=[a.name for a in DelayAlgorithm],
        help='Select a function to calculate delay times with.'
    )

    return parser.parse_args()


def config_builder(args: argparse.Namespace) -> JobFunnelConfigManager:
    """Parse the JobFunnel configuration settings into a JobFunnelConfigManager.

        args [argparse.Namespace]: cli arguments from argparser
    """
    # NOTE: log_file and output_folder are specially handled
    path_attrs = [
        'master_csv_file', 'cache_folder',
        'block_list_file', 'duplicates_list_file',
    ]
    # Init and pop args that are cli-only and not in our schema
    args_dict = vars(args)
    settings_yaml_file = args_dict.pop('settings_yaml_file')
    output_folder = args_dict.pop('output_folder')
    args_dict.pop('do_recovery_mode')  # NOTE: this is handled in __main__
    config = {'search': {}, 'delay': {}, 'proxy': {}}

    # Build a config that respects CLI, defaults and YAML
    if settings_yaml_file:

        # Ensure user isn't pasing output_folder as this cannot be used here
        if output_folder != DEFAULT_OUTPUT_DIRECTORY:
            raise ValueError(
                "Cannot combine -s YAML and -o argument, all file paths must "
                "be specified individually."
            )

        # Load YAML
        config.update(
            yaml.load(open(settings_yaml_file, 'r'), Loader=yaml.FullLoader)
        )
        # Set defaults for our YAML
        config = SettingsValidator.normalized(config)

        # Validate the config passed via YAML
        if not SettingsValidator.validate(config):
            raise ValueError(
                f"Invalid Config settings yaml:\n{SettingsValidator.errors}"
            )

    # Handle CLI arguments, overwriting YAML if needed
    if output_folder:
        if (output_folder != DEFAULT_OUTPUT_DIRECTORY
                and (args_dict['master_csv_file'] or args_dict['cache_folder']
                     or args_dict['block_list_file']
                     or args_dict['duplicates_list_file'])):
            # NOTE: we handle the -s with -o case before we get here
            raise ValueError(
                "Cannot combine -o with -blf, -cache, -dlf arguments, as -o"
                " defines these paths."
            )
        else:
            # Set paths based on passed output_folder:
            # NOTE: these will match defaults if using DEFAULT_OUTPUT_PATH
            config['master_csv_file'] = os.path.join(
                output_folder, 'master.csv'
            )
            config['cache_folder'] = os.path.join(
                output_folder, '.cache'
            )
            config['block_list_file'] = os.path.join(
                config['cache_folder'], 'block.json'
            )
            config['duplicates_list_file'] = os.path.join(
                config['cache_folder'], 'duplicates.json'
            )
            if not args_dict['log_file']:
                # User can specify a different log location if they want.
                config['log_file'] = os.path.join(
                    output_folder, 'log.log'
                )
    else:
        # We should have all the paths we need
        for path_arg in path_attrs:
            config[path_arg] = args_dict[path_arg]

        if not args_dict['log_file']:
            # We will define log to be where the csv is.
            config['log_file'] = os.path.join(
                os.path.dirname(os.path.abspath(config['cache_folder'])),
                'log.log',
            )

    # Turn args_dict into config dict by nesting as-needed
    for key, arg_value in args_dict.items():
        if arg_value is not None:
            if key == 'log_level' and arg_value != DEFAULT_LOG_LEVEL_NAME:
                # We got a non-default log level, overwrite any YAML setting
                config[key] = arg_value
            elif key == 'no_scrape':
                # Default is False.
                config[key] = arg_value
            else:
                # Set sub-config value
                for sub_key in ['search', 'delay', 'proxy']:
                    if sub_key in key:
                        config[sub_key][key.split(sub_key + '_')[1]] = arg_value
                        break

    # Create folders that out output files are within if they don't exist
    path_attrs.append('log_file')
    for path_attr in path_attrs:
        output_dir = os.path.dirname(os.path.abspath(config[path_attr]))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    # Build JobFunnelConfigManager
    search_cfg = SearchConfig(
        keywords=config['search']['keywords'],
        province_or_state=config['search']['province_or_state'],
        city=config['search']['city'],
        distance_radius=config['search']['radius'],
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

    if config['proxy']:
        proxy_cfg = ProxyConfig(
            protocol=config['proxy']['protocol'],
            ip_address=config['proxy']['ip'],
            port=config['proxy']['port'],
        )
    else:
        proxy_cfg = None

    funnel_cfg_mgr = JobFunnelConfigManager(
        master_csv_file=config['master_csv_file'],
        user_block_list_file=config['block_list_file'],
        duplicates_list_file=config['duplicates_list_file'],
        cache_folder=config['cache_folder'],
        log_file=config['log_file'],
        log_level=config['log_level'],
        no_scrape=config['no_scrape'],
        search_config=search_cfg,
        delay_config=delay_cfg,
        proxy_config=proxy_cfg,
    )

    # Validate funnel config as well (checks some stuff Cerberus doesn't rn)
    funnel_cfg_mgr.validate()

    return funnel_cfg_mgr
