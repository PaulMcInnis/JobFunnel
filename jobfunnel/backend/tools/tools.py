"""Assorted tools for all aspects of funnelin''
FIXME: most of these are not using Job correctly!!!

"""
# FIXME sort these
import logging
import os
import re
import random
import string
from copy import deepcopy
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import IEDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from webdriver_manager.opera import OperaDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver

from jobfunnel.backend import Job


# def get_random_user_agent() -> str:
#     """The user agent should be randomized per-Scraper to help with spam det.
#     """ FIXME... should go here maybe?


def split_url(url):
    # capture protocol, ip address and port from given url
    match = re.match(r'^(http[s]?):\/\/([A-Za-z0-9.]+):([0-9]+)?(.*)$', url)

    # if not all groups have a match, match will be None
    if match is not None:
        return {
            'protocol': match.group(1),
            'ip_address': match.group(2),
            'port': match.group(3),
        }
    else:
        return None


def proxy_dict_to_url(proxy_dict):
    protocol = proxy_dict['protocol']
    ip = proxy_dict['ip_address']
    port = proxy_dict['port']

    url_str = ''
    if protocol != '':
        url_str += protocol + '://'
    if ip != '':
        url_str += ip
    if port != '':
        url_str += ':' + port

    return url_str


def change_nested_dict(data, args, val):
    """ Access nested dictionary using multiple arguments.

    https://stackoverflow.com/questions/10399614/accessing-value-inside-nested-dictionaries
    """
    if args and data:
        element = args[0]
        if element:
            if len(args) == 1:
                data[element] = val
            else:
                change_nested_dict(data[element], args[1:], val)


def config_factory(base_config, attr_list):
    """ Create new config files from attribute dictionary.

    """
    configs = []
    for attr in attr_list:
        # create deep copy of nested dict
        config_cp = deepcopy(base_config)

        # change value and append
        change_nested_dict(config_cp, attr[0], attr[1])
        configs.append(config_cp)

    return configs


def get_webdriver():
    """Get whatever webdriver is availiable in the system.
    webdriver_manager and selenium are currently being used for this.
    Supported browsers:[Firefox, Chrome, Opera, Microsoft Edge, Internet Expolorer]
    Returns:
            a webdriver that can be used for scraping. Returns None if we don't find a supported webdriver.

    """
    try:
        driver = webdriver.Firefox(
            executable_path=GeckoDriverManager().install())
    except Exception:
        try:
            driver = webdriver.Chrome(ChromeDriverManager().install())
        except Exception:
            try:
                driver = webdriver.Ie(IEDriverManager().install())
            except Exception:
                try:
                    driver = webdriver.Opera(
                        executable_path=OperaDriverManager().install())
                except Exception:
                    try:
                        driver = webdriver.Edge(
                            EdgeChromiumDriverManager().install())
                    except Exception:
                        driver = None
                        logging.error(
                            "Your browser is not supported. Must have one of the following installed to scrape: [Firefox, Chrome, Opera, Microsoft Edge, Internet Expolorer]")

    return driver
