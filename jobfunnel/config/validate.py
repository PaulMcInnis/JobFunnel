import re

from .valid_options import DOMAINS, PROVIDERS, DELAY_FUN
from .parser import ConfigError


def validate_region(region):
    """ Check if the region settings are valid.

    """
    # only allow supported domains
    if region['domain'] not in DOMAINS:
        raise ConfigError('domain')

    # search term state is inserted as province if province does not already
    # exist
    if 'state' in region:
        if (region['state'] is not None) and (region['province'] is None):
            region['province'] = region['state']

    # north american jobs should have a province/state provided
    if region['domain'] in ['com', 'ca'] and region['province'] is None:
        raise ConfigError('province')


def validate_delay(delay):
    """ Check if the delay has a valid configuration.

    """
    # delay function should be constant, linear or sigmoid
    if delay['function'] not in DELAY_FUN:
        raise ConfigError('delay_function')

    # maximum delay should be larger or equal to minimum delay
    if delay['delay'] < delay['min_delay']:
        raise ConfigError('(min)_delay')

    # minimum delay should be at least 1 and maximum delay at least 10
    if delay['delay'] < 10 or delay['min_delay'] < 1:
        raise ConfigError('(min)_delay')


def validate_config(config):
    """ Check whether the config is a valid configuration.

    Some options are already checked at the command-line tool, e.g., loggging.
    Some checks are trivial while others have a separate function.
    """
    # check if paths are valid
    check_paths = {
        'data_path': r'data$',
        'master_list_path': r'master_list\.csv$',
        'duplicate_list_path': r'duplicate_list\.csv$',
        'log_path': r'data[\\\/]jobfunnel.log$',
        'filter_list_path': r'data[\\\/]filter_list\.json$',
    }

    for path, pattern in check_paths.items():
        if not re.search(pattern, config[path]):
            raise ConfigError(path)

    # check if the provider list only consists of supported providers
    if not set(config['providers']).issubset(PROVIDERS):
        raise ConfigError('providers')

    # check validity of region settings
    validate_region(config['search_terms']['region'])

    # check validity of delay settings
    validate_delay(config['delay_config'])

    #check the validity of max_listing_days settings
    if(config['max_listing_days'] is not None and config['max_listing_days']<0):
        raise ConfigError('max_listing_days')
