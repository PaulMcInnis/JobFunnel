# Paul McInnis 2018
# writes pickles to master list path and applies search filters

import csv
import json
import logging
import os
import pickle
import random
import re
import sys

from collections import OrderedDict
from concurrent.futures import as_completed
from datetime import date
from time import time
from typing import Dict, List
from requests import Session

from .tools.delay import delay_alg
from .tools.filters import tfidf_filter, id_filter, date_filter
from .tools.tools import proxy_dict_to_url

# setting job status to these words removes them from masterlist + adds to
# blacklist
REMOVE_STATUSES = ['archive', 'archived', 'remove', 'rejected']

# csv header
MASTERLIST_HEADER = ['status', 'title', 'company', 'location', 'date',
                     'blurb', 'tags', 'link', 'id', 'provider', 'query']

# user agent list
USER_AGENT_LIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'text/user_agent_list.txt'))


class JobFunnel(object):
    """Class that initializes a Scraper and scrapes a website to get jobs
    """

    def __init__(self, config: JobFunnelConfig):  # FIXME: implement this
        # Paths
        self.master_file = config.master_file
        self.user_deny_list_file = config.user_deny_list_file
        self.global_deny_list_file = config.global_deny_list_file
        self.cache_folder = config.cache_folder
        self.log_file = config.log_file

        self.log_level = config.log_level
        self.date_string = date.today().strftime("%Y-%m-%d")

        # Set delay settings if they exist
        self.delay_config = None
        if config.delay_config is not None:
            self.delay_config = config.delay_config

        # Open a session with/out a proxy configured
        self.session = Session()

        # set proxy if given FIXME
        # if config.proxy is not None:
        #     self.s.proxies = {
        #         config.proxy.protocol: proxy_dict_to_url(config.proxy)
        #     }

        # # create data dir FIXME
        # if not os.path.exists(args['data_path']):
        #     os.makedirs(args['data_path'])

    def init_logging(self):
        """Initialize a logger"""
        pass

    def scrape(self):
        """Scrape jobs"""
        pass
