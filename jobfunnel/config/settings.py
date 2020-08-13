"""Settings YAML Schema w/ validator
"""
from cerberus import Validator
import ipaddress
import logging

from jobfunnel.resources import (
    Locale, Provider, DelayAlgorithm, LOG_LEVEL_NAMES
)


SETTINGS_YAML_SCHEMA = {
    'master_csv_file': {'required': True, 'type': 'string'},
    'block_list_file': {'required': True, 'type': 'string'},
    'cache_folder': {'required': True, 'type': 'string'},
    'duplicates_list_file': {'required': False, 'type': 'string'},
    'no_scrape': {'required': False, 'type': 'boolean'},
    'recover': {'required': False, 'type': 'boolean'},
    'log_level': {'required': False, 'allowed': LOG_LEVEL_NAMES},
    'log_file': {'required': False, 'type': 'string'},
    'save_duplicates': {'required': False, 'type': 'boolean'},
    'use_web_driver': {'required': False, 'type': 'boolean'},
    'search': {
        'type': 'dict',
        'required': True,
        'schema': {
            'providers': {
                'required': True, 'allowed': [p.name for p in Provider]
            },
            'locale' : {'required': True, 'allowed': [l.name for l in Locale]},
            'region': {
                'type': 'dict',
                'required': True,
                'schema': {
                    'province_or_state': {'required': True, 'type': 'string'},
                    'city': {'required': True, 'type': 'string'},
                    'radius': {'required': False, 'type': 'integer', 'min': 0},
                },
            },
            'similar_results': {'required': False, 'type': 'boolean'},
            'keywords': {
                'required': True,
                'type': 'list',
                'schema': {'type': 'string'},
            },
            'max_listing_days': {
                'required': False, 'type': 'integer', 'min': 0
            },
            'company_block_list': {
                'required': False,
                'type': 'list', 'schema': {'type': 'string'},
            },
        },
    },
    'delay': {
        'type': 'dict',
        'required': False,
        'nullable': True,
        'schema' : {
            'algorithm': {
                'required': False,
                'allowed': [d.name for d in DelayAlgorithm],
                'nullable': True,
             },
            # TODO: implement custom rule max > min
            'max_duration': {
                'required': False,
                'type': 'float',
                'min': 0,
                'nullable': True,
             },
            'min_duration': {
                'required': False,
                'type': 'float',
                'min': 0,
                'nullable': True,
             },
             'random': {
                'required': False,
                'type': 'boolean',
                'nullable': True,
                },
             'converging': {
                'required': False,
                'type': 'boolean',
                'nullable': True,
            },
        },
    },

    'proxy': {
        'type': 'dict',
        'required': False,
        'nullable': True,
        'schema' : {
            'protocol': {
                'required': False,
                'allowed': ['http', 'https'],
                'nullable': True,
             },
            'ip': {
                'required': False,
                'type': 'ipv4address',
                'nullable': True,
             },
            'port': {
                'required': False,
                'type': 'integer',
                'min': 0,
                'nullable': True,
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
