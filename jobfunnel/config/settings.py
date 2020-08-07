"""Settings YAML Schema w/ validator
"""
from cerberus import Validator
import ipaddress
import logging

from jobfunnel.resources import (
    Locale, Provider, DelayAlgorithm, LOG_LEVEL_NAMES
)


SETTINGS_YAML_SCHEMA = {
    'output_path': {'required': True, 'type': 'string'},
    'locale' : {'required': True, 'allowed': [l.name for l in Locale]},
    'providers': {'required': True, 'allowed': [p.name for p in Provider]},
    # 'no_scrape': {'required': False, 'type': 'boolean'},  # NOTE:  CLI only.
    # 'recover': {'required': False, 'type': 'boolean'},  # NOTE: CLI only.
    'search': {
        'type': 'dict',
        'required': True,
        'schema': {
            'region': {
                'type': 'dict',
                'required': True,
                'schema': {
                    'province_or_state': {'required': True, 'type': 'string'},
                    'city': {'required': True, 'type': 'string'},
                    'radius': {'required': False, 'type': 'integer', 'min': 0},
                },
            },
            'keywords': {
                'required': True,
                'type': 'list', 'schema': {'type': 'string'},
            },
            'similar': {'required': False, 'type': 'boolean'},
        },
    },
    'company_block_list': {
        'required': False,
        'type': 'list', 'schema': {'type': 'string'},
    },
    'log_level': {'required': False, 'allowed': LOG_LEVEL_NAMES},
    'save_duplicates': {'required': False, 'type': 'boolean'},
    'delay': {
        'type': 'dict',
        'required': False,
        'schema' : {
            'algorithm': {
                'required': False,
                'allowed': [d.name for d in DelayAlgorithm],
             },
            # TODO: implement custom rule max > min
            'max_duration': {
                'required': False,
                'type': 'float',
                'min': 0,
             },
            'min_duration': {
                'required': False,
                'type': 'float',
                'min': 0,
             },
             'random_delay': {'required': False, 'type': 'boolean'},
             'converging_random_delay': {'required': False, 'type': 'boolean'},
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
             'random_delay': {'required': False, 'type': 'boolean'},
             'converging_random_delay': {'required': False, 'type': 'boolean'},
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
