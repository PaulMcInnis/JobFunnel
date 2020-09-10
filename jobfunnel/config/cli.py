"""Configuration parsing module for CLI --> JobFunnelConfigManager
"""
import argparse
import os
from typing import Dict, Any
import yaml

from jobfunnel.config import (DelayConfig, JobFunnelConfigManager,
                              ProxyConfig, SearchConfig, SettingsValidator)
from jobfunnel.resources import (LOG_LEVEL_NAMES, DelayAlgorithm, Locale,
                                 Provider)
from jobfunnel.resources.defaults import *


PATH_ATTRS = [
    'master_csv_file', 'cache_folder', 'log_file', 'block_list_file',
    'duplicates_list_file',
]


def parse_cli() -> Dict[str, Any]:
    """Parse the command line arguments into an Dict[arg_name, arg_value]

    TODO: need to ensure users can try out JobFunnel as easily as possible.
    """
    base_parser = argparse.ArgumentParser('Job Search CLI.')

    # Independant arguments
    base_parser.add_argument(
        '--recover',
        dest='do_recovery_mode',
        action='store_true',
        help='Reconstruct a new master CSV file from all available cache files.'
             'WARNING: this will replace all the statuses/etc in your master '
             'CSV, it is intended for starting fresh / recovering from a bad '
             'state.',
    )
    
    base_subparsers = base_parser.add_subparsers(required=False)
    
    # Configure everything via a YAML (NOTE: no other parsers may be passed)
    yaml_parser = base_subparsers.add_parser(
        'load',
        help='Run using an existing configuration YAML.',
    )
    
    yaml_parser.add_argument(
        '-s',
        dest='settings_yaml_file',
        type=str,
        help='Path to a settings YAML file containing your job search config.'
    )
    
    yaml_parser.add_argument(
        '--no-scrape',
        action='store_true',
        help='Do not make any get requests, instead, load jobs from cache '
             'and update filters + CSV file. NOTE: overrides setting in YAML.',
    )
    
    yaml_parser.add_argument(
        '-log-level',
        type=str,
        choices=LOG_LEVEL_NAMES,
        help='Type of logging information shown on the terminal. NOTE: '
             'is passed, overrides the setting in YAML.',
    )
    
    # We are using CLI for all arguments.
    cli_parser = base_subparsers.add_parser(
        'custom',
        help='Configure search query and data providers via CLI.',
    )

    cli_parser.add_argument(
        '-log-level',
        type=str,
        choices=LOG_LEVEL_NAMES,
        default=DEFAULT_LOG_LEVEL_NAME,
        help='Type of logging information shown on the terminal.',
    )
    cli_parser.add_argument(
        '--no-scrape',
        action='store_true',
        help='Do not make any get requests, instead, load jobs from cache '
             'and update filters + CSV file.',
    )

    # Paths
    search_group = cli_parser.add_argument_group('paths')
    search_group.add_argument(
        '-csv',
        dest='master_csv_file',
        type=str,
        help='Path to a master CSV file containing your search results.',
        required=True,
    )

    search_group.add_argument(
        '-cache',
        dest='cache_folder',
        type=str,
        help='Directory where cached scrape data will be stored.',
        required=True,
    )

    search_group.add_argument(
        '-blf',
        dest='block_list_file',
        type=str,
        help='JSON file of jobs you want to omit from your job search.',
        required=True,
    )

    search_group.add_argument(
        '-dl',
        dest='duplicates_list_file',
        type=str,
        help='JSON file of jobs which have been detected to be duplicates of '
             'existing jobs.',
        required=True,
    )

    search_group.add_argument(
        '-log-file',
        type=str,
        help='Path to log file.',
        required=True,  # FIXME: This should be optional (no writing to it all).
    )

    # SearchConfig via CLI args subparser
    search_group = cli_parser.add_argument_group('search')
    search_group.add_argument(
        '-kw',
        dest='search.keywords',
        type=str,
        nargs='+',
        help='List of job-search keywords (i.e. Engineer, AI).',
        required=True,
    )

    search_group.add_argument(
        '-l',
        dest='search.locale',
        type=str,
        choices=[l.name for l in Locale],
        help='Global location and language to use to scrape the job provider'
             ' website (i.e. -l CANADA_ENGLISH -p indeed --> indeed.ca).',
        required=True,
    )

    search_group.add_argument(
        '-ps',
        dest='search.province_or_state',
        type=str,
        help='Province/state value for your job-search area of interest. '
             '(i.e. Ontario).',
        required=True,
    )

    search_group.add_argument(
        '-c',
        dest='search.city',
        type=str,
        help='City/town value for job-search region (i.e. Waterloo).',
        required=True,
    )

    search_group.add_argument(
        '-cbl',
        type=str,
        dest='search.company_block_list',
        nargs='+',
        help='List of company names to omit from all search results '
             '(i.e. SpamCompany, Cash5Gold).',
        required=False,
    )

    search_group.add_argument(
        '-p',
        dest='search.providers',
        type=str,
        nargs='+',
        choices=[p.name for p in Provider],
        default=DEFAULT_PROVIDER_NAMES,
        help='List of job-search providers (i.e. Indeed, Monster, GlassDoor).',
        required=False,
    )

    search_group.add_argument(
        '-r',
        dest='search.radius',
        type=int,
        default=DEFAULT_SEARCH_RADIUS,
        help='The maximum distance a job should be from the specified city. '
             'NOTE: units are [km] CANADA locales and [mi] for US locales.',
        required=False,
    )

    search_group.add_argument(
        '-max-listing-days',
        dest='search.max_listing_days',
        type=int,
        default=DEFAULT_MAX_LISTING_DAYS,
        help='The maximum number of days-old a job can be. (i.e pass 30 to '
        'filter out jobs older than a month).',
        required=False,
    )

    search_group.add_argument(
        '--similar-results',
        dest='search.similar_results',
        action='store_true',
        help='Return more general results from search query '
             '(NOTE: this is only available for Indeed provider).',
    )

    # Proxy stuff. TODO: way to tell argparse if proxy is seen all are req'd?
    proxy_group = cli_parser.add_argument_group('proxy')
    proxy_group.add_argument(
        '-protocol',
        dest='proxy.protocol',
        type=str,
        help='Proxy protocol.',
    )
    proxy_group.add_argument(
        '-ip',
        dest='proxy.ip',
        type=str,
        help='Proxy IP (V4) address.',
    )
    proxy_group.add_argument(
        '-port',
        dest='proxy.port',
        type=str,
        help='Proxy port address.',
    )

    # Delay stuff
    delay_group = cli_parser.add_argument_group('delay')
    delay_group.add_argument(
        '--random',
        dest='delay.random',
        action='store_true',
        help='Turn on random delaying.',
    )

    delay_group.add_argument(
        '--converging',
        dest='delay.converging',
        action='store_true',
        help='Use converging random delay. NOTE: this is intended to be used '
             'with --random',
    )

    delay_group.add_argument(
        '-max',
        dest='delay.max',
        type=float,
        default=DEFAULT_DELAY_MAX_DURATION,
        help='Set the maximum delay duration in seconds.',
    )

    delay_group.add_argument(
        '-min',
        dest='delay.min',
        type=float,
        default=DEFAULT_DELAY_MIN_DURATION,
        help='Set the minimum delay duration in seconds',
    )

    delay_group.add_argument(
        '-algorithm',
        dest='delay.algorithm',
        choices=[a.name for a in DelayAlgorithm],
        default=DEFAULT_DELAY_ALGORITHM.name,
        help='Select a function to calculate delay times with.',
    )

    return vars(base_parser.parse_args())


def config_parser(args_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the JobFunnel configuration settings and combine CLI, YAML and
    defaults to build a valid config dictionary for initializing config objects.
    """
    # Build a config that respects CLI, defaults and YAML
    # NOTE: we a passed settings YAML first so we can inject CLI after if needed
    if 'settings_yaml_file' in args_dict:

        # Load YAML
        config = yaml.load(
            open(args_dict['settings_yaml_file'], 'r'), 
            Loader=yaml.FullLoader,
        )
            
        # Inject any base level args (--no-scrape, -log-level)
        config['no_scrape'] = args_dict['no_scrape']
        if args_dict['log-level']:
            config['log-level'] = args_dict['log_level']
        
        # Set defaults for our YAML
        config = SettingsValidator.normalized(config)

        # Validate the config passed via YAML
        if not SettingsValidator.validate(config):
            raise ValueError(
                f"Invalid Config settings yaml:\n{SettingsValidator.errors}"
            )

    else:

        # Handle CLI arguments for paths, possibly overwriting YAML
        sub_keys = ['search', 'delay', 'proxy']
        config = {k: {} for k in sub_keys}  # type: Dict[str, Dict[str, Any]]

        # Handle all the sub-configs, and non-path, non-default CLI args
        for key, value in args_dict.items():
            if key == 'do_recovery_mode':
                # This is not present in the schema, it is CLI only.
                continue  
            elif value:
                if any([sub_key in key for sub_key in sub_keys]):
                    # Set sub-config value
                    key_sub_strings = key.split('.')
                    assert len(key_sub_strings) == 2, "Bad dest name: " + key
                    config[key_sub_strings[0]][key_sub_strings[1]] = value
                else:
                    # Set base-config value
                    assert '.' not in key, "Bad base-key: " + key
                    config[key] = value

    return config


def config_builder(config: Dict[str, Any]) -> JobFunnelConfigManager:
    """Method to build Config* objects from a valid config dictionary
    """

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

    if config.get('proxy'):
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

    # Create folders that out output files are within if they don't exist
    # TODO: perhaps we should move this elsewhere?
    for path_attr in PATH_ATTRS:
        output_dir = os.path.dirname(os.path.abspath(config[path_attr]))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    # Validate funnel config as well (checks some stuff Cerberus doesn't rn)
    funnel_cfg_mgr.validate()

    return funnel_cfg_mgr
    
