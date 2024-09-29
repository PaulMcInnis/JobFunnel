"""Settings YAML Schema w/ validator
"""

import ipaddress

from cerberus import Validator

from jobfunnel.resources import (
    LOG_LEVEL_NAMES,
    DelayAlgorithm,
    Locale,
    Provider,
    Remoteness,
)
from jobfunnel.resources.defaults import (
    DEFAULT_COMPANY_BLOCK_LIST,
    DEFAULT_DELAY_ALGORITHM,
    DEFAULT_DELAY_MAX_DURATION,
    DEFAULT_DELAY_MIN_DURATION,
    DEFAULT_LOG_LEVEL_NAME,
    DEFAULT_MAX_LISTING_DAYS,
    DEFAULT_PROVIDERS,
    DEFAULT_RANDOM_CONVERGING_DELAY,
    DEFAULT_RANDOM_DELAY,
    DEFAULT_REMOTENESS,
    DEFAULT_RETURN_SIMILAR_RESULTS,
    DEFAULT_SEARCH_RADIUS,
)

SETTINGS_YAML_SCHEMA = {
    "master_csv_file": {
        "required": True,
        "type": "string",
    },
    "block_list_file": {
        "required": True,
        "type": "string",
    },
    "cache_folder": {
        "required": True,
        "type": "string",
    },
    "duplicates_list_file": {
        "required": True,
        "type": "string",
    },
    "log_file": {
        "required": True,  # TODO: allow this to be optional
        "type": "string",
    },
    "no_scrape": {
        "required": False,  # TODO: we should consider making this CLI only
        "type": "boolean",
        "default": False,
    },
    "log_level": {
        "required": False,
        "allowed": LOG_LEVEL_NAMES,
        "default": DEFAULT_LOG_LEVEL_NAME,
    },
    "search": {
        "type": "dict",
        "required": True,
        "schema": {
            "providers": {
                "required": False,
                "allowed": [p.name for p in Provider],
                "default": DEFAULT_PROVIDERS,
            },
            "locale": {
                "required": True,
                "allowed": [locale.name for locale in Locale],
            },
            "province_or_state": {"required": True, "type": "string"},
            "city": {"required": True, "type": "string"},
            "radius": {
                "required": False,
                "type": "integer",
                "min": 0,
                "default": DEFAULT_SEARCH_RADIUS,
            },
            "similar_results": {
                "required": False,
                "type": "boolean",
                "default": DEFAULT_RETURN_SIMILAR_RESULTS,
            },
            "keywords": {
                "required": True,
                "type": "list",
                "schema": {"type": "string"},
            },
            "max_listing_days": {
                "required": False,
                "type": "integer",
                "min": 0,
                "default": DEFAULT_MAX_LISTING_DAYS,
            },
            "company_block_list": {
                "required": False,
                "type": "list",
                "schema": {"type": "string"},
                "default": DEFAULT_COMPANY_BLOCK_LIST,
            },
            "remoteness": {
                "required": False,
                "type": "string",
                "allowed": [r.name for r in Remoteness],
                "default": DEFAULT_REMOTENESS.name,
            },
        },
    },
    "delay": {
        "type": "dict",
        "required": False,
        "schema": {
            "algorithm": {
                "required": False,
                "allowed": [d.name for d in DelayAlgorithm],
                "default": DEFAULT_DELAY_ALGORITHM.name,
            },
            # TODO: implement custom rule max > min
            "max_duration": {
                "required": False,
                "type": "float",
                "min": 0,
                "default": DEFAULT_DELAY_MAX_DURATION,
            },
            "min_duration": {
                "required": False,
                "type": "float",
                "min": 0,
                "default": DEFAULT_DELAY_MIN_DURATION,
            },
            "random": {
                "required": False,
                "type": "boolean",
                "default": DEFAULT_RANDOM_DELAY,
            },
            "converging": {
                "required": False,
                "type": "boolean",
                "default": DEFAULT_RANDOM_CONVERGING_DELAY,
            },
        },
    },
    "proxy": {
        "type": "dict",
        "required": False,
        "schema": {
            "protocol": {
                "required": False,
                "allowed": ["http", "https"],
            },
            "ip": {
                "required": False,
                "type": "ipv4address",
            },
            "port": {
                "required": False,
                "type": "integer",
                "min": 0,
            },
        },
    },
}


class JobFunnelSettingsValidator(Validator):
    """A simple JSON data validator with a custom data type for IPv4 addresses
    https://codingnetworker.com/2016/03/validate-json-data-using-cerberus/
    """

    def _validate_type_ipv4address(self, value):
        """
        checks that the given value is a valid IPv4 address
        """
        try:
            # try to create an IPv4 address object using the python3 ipaddress
            # module
            ipaddress.IPv4Address(value)
            return True
        except Exception:
            self._error(value, "Not a valid IPv4 address")


SettingsValidator = JobFunnelSettingsValidator(SETTINGS_YAML_SCHEMA)
