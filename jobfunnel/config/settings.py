"""Settings YAML Schema w/ validator
"""
from cerberus import Validator
import ipaddress
import logging

from jobfunnel.resources import (
    Locale, Provider, DelayAlgorithm, LOG_LEVEL_NAMES
)
from jobfunnel.resources.defaults import *


SETTINGS_YAML_SCHEMA = {
    'master_csv_file': {
        'required': True,
        'type': 'string',
    },
    'block_list_file': {
        'required': True,
        'type': 'string',
    },
    'cache_folder': {
        'required': True,
        'type': 'string',
        },
    'duplicates_list_file': {
        'required': False,
        'type': 'string',
        'default': DEFAULT_DUPLICATES_FILE,
    },
    'no_scrape': {
        'required': False,
        'type': 'boolean',
        'default': DEFAULT_NO_SCRAPE,
    },
    'log_level': {
        'required': False,
        'allowed': LOG_LEVEL_NAMES,
        'default': DEFAULT_LOG_LEVEL_NAME,
    },
    'log_file': {
        'required': False,
        'type': 'string',
        'default': DEFAULT_LOG_FILE,
    },
    'save_duplicates': {
        'required': False,
        'type': 'boolean',
        'default': DEFAULT_SAVE_DUPLICATES,
    },
    'search': {
        'type': 'dict',
        'required': True,
        'schema': {
            'providers': {
                'required': False,
                'allowed': [p.name for p in Provider],
                'default': DEFAULT_PROVIDERS,
            },
            'locale' : {
                'required': True,
                'allowed': [l.name for l in Locale],
            },
            'province_or_state': {'required': True, 'type': 'string'},
            'city': {'required': True, 'type': 'string'},
            'radius': {
                'required': False,
                'type': 'integer',
                'min': 0,
                'default': DEFAULT_SEARCH_RADIUS_KM,
            },
            'similar_results': {
                'required': False,
                'type': 'boolean',
                'default': DEFAULT_RETURN_SIMILAR_RESULTS,
            },
            'keywords': {
                'required': True,
                'type': 'list',
                'schema': {'type': 'string'},
            },
            'max_listing_days': {
                'required': False,
                'type': 'integer',
                'min': 0,
                'default': DEFAULT_MAX_LISTING_DAYS,
            },
            'company_block_list': {
                'required': False,
                'type': 'list',
                'schema': {'type': 'string'},
                'default': DEFAULT_COMPANY_BLOCK_LIST,
            },
        },
    },
    'delay': {
        'type': 'dict',
        'required': False,
        'schema' : {
            'algorithm': {
                'required': False,
                'allowed': [d.name for d in DelayAlgorithm],
                'default': DEFAULT_DELAY_ALGORITHM.name,
             },
            # TODO: implement custom rule max > min
            'max_duration': {
                'required': False,
                'type': 'float',
                'min': 0,
                'default': DEFAULT_DELAY_MAX_DURATION,
             },
            'min_duration': {
                'required': False,
                'type': 'float',
                'min': 0,
                'default': DEFAULT_DELAY_MIN_DURATION,
             },
             'random': {
                'required': False,
                'type': 'boolean',
                'default': DEFAULT_RANDOM_DELAY,
             },
             'converging': {
                'required': False,
                'type': 'boolean',
                'default': DEFAULT_RANDOM_CONVERGING_DELAY,
            },
        },
    },
    'proxy': {
        'type': 'dict',
        'required': False,
        'schema' : {
            'protocol': {
                'required': False,
                'allowed': ['http', 'https'],
             },
            'ip': {
                'required': False,
                'type': 'ipv4address',
             },
            'port': {
                'required': False,
                'type': 'integer',
                'min': 0,
             },
        },
    },
}


class JobFunnelSettingsValidator(Validator):
    """A simple JSON data validator with a custom data type for IPv4 addresses
    https://codingnetworker.com/2016/03/validate-json-data-using-cerberus/
    """
    def _validate_type_ipv4address(self, field, value):
        """
        checks that the given value is a valid IPv4 address
        """
        try:
            # try to create an IPv4 address object using the python3 ipaddress module
            ipaddress.IPv4Address(value)
        except:
            self._error(field, "Not a valid IPv4 address")


SettingsValidator = JobFunnelSettingsValidator(SETTINGS_YAML_SCHEMA)
