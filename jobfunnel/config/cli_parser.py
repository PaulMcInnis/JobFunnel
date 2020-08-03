"""tools to parse CLI --> JobFunnelConfig
"""
import argparse
import yaml

from jobfunnel.config import (
    JobFunnelConfig, SearchConfig, ProxyConfig, DelayConfig)

# FIXME: implement cereberus to validate YAML with a schema

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

    parser.add_argument('-p',
                        dest='province',
                        type=str,
                        required=False,
                        help='province value for a region ')

    parser.add_argument('--city',
                        dest='city',
                        type=str,
                        required=False,
                        help='city value for a region ')

    parser.add_argument('--domain',
                        dest='domain',
                        type=str,
                        required=False,
                        help='domain value for a region ')

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
                        default=None,
                        help='pass to get \'similar\' job listings')

    parser.add_argument('--no_scrape',
                        dest='no_scrape',
                        action='store_true',
                        default=None,
                        help='skip web-scraping and load a previously saved '
                             'daily scrape pickle')

    parser.add_argument('--proxy',
                        dest='proxy',
                        type=str,
                        required=False,
                        default=None,
                        help='proxy address')

    parser.add_argument('--recover',
                        dest='recover',
                        action='store_true',
                        default=None,
                        help='recover master-list by accessing all historic '
                             'scrapes pickles')

    parser.add_argument('--save_dup',
                        dest='save_duplicates',
                        action='store_true',
                        required=False,
                        default=None,
                        help='save duplicates popped by tf_idf filter to file')
    parser.add_argument('--max_listing_days',
                        dest='max_listing_days',
                        type=int,
                        default=None,
                        required=False,
                        help='The maximum number of days old a job can be.'
                        '(i.e pass 30 to filter out jobs older than a month)')

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
        },
        'max_listing_days': cli.max_listing_days,
    }

    if cli.proxy is not None:
        yaml['proxy'] = split_url(cli.proxy)
    return yaml
