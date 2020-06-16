import pytest
import os
import re
import sys
import json
import random

from bs4 import BeautifulSoup
from requests import get, post
from typing import Union
from unittest.mock import patch

from jobfunnel.config.parser import parse_config
from jobfunnel.indeed import Indeed
from jobfunnel.monster import Monster
from jobfunnel.glassdoor_static import GlassDoorStatic


PROVIDERS = {'indeed': Indeed, 'monster': Monster,
             'glassdoorstatic': GlassDoorStatic}

# TODO: Test GlassdoorDynamic Provider

DOMAINS = {'America': 'com', 'Canada': 'ca'}

cities_america = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'json/cities_america.json'))
cities_canada = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'json/cities_canada.json'))

with open(cities_america, 'r') as file:
    cities_america = json.load(file)

with open(cities_canada, 'r') as file:
    cities_canada = json.load(file)

cities = cities_america + cities_canada
test_size = 100
if len(cities) < test_size:
    test_size = len(cities)

# take a random sample of cities of size test_size
cities = random.sample(cities, test_size)

with patch.object(sys, 'argv', ['']):
    config = parse_config()


@pytest.mark.xfail(strict=False)
@pytest.mark.parametrize('city', cities)
def test_cities(city, delay=1):
    """tests american city"""
    count = 0  # a count of providers with successful test cases
    for p in config['providers']:
        provider: Union[GlassDoorStatic, Monster,
                        Indeed] = PROVIDERS[p](config)
        provider.search_terms['region']['domain'] = DOMAINS[city['country']]
        provider.search_terms['region']['province'] = city['abbreviation']
        provider.search_terms['region']['city'] = city['city']
        if isinstance(provider, Indeed):
            # get search url
            search = provider.get_search_url()

            # get the html data, initialize bs4 with lxml
            request_html = get(search, headers=provider.headers)
        elif isinstance(provider, Monster):
            # get search url
            search = provider.get_search_url()

            # get the html data, initialize bs4 with lxml
            request_html = get(search, headers=provider.headers)
        elif isinstance(provider, GlassDoorStatic):
            try:
                # get search url
                search, data = provider.get_search_url(method='post')
            except IndexError:
                # sometimes glassdoor does not find the location id
                continue

            # get the html data, initialize bs4 with lxml
            request_html = post(search, headers=provider.headers, data=data)
        else:
            raise TypeError(
                f'Type {type(provider)} does not match any of the providers.')

        # create the soup base
        soup_base = BeautifulSoup(request_html.text, provider.bs4_parser)

        # parse the location text field
        where = None  # initialize location variable
        location = ', '.join([city['city'], city['abbreviation']])
        location = re.sub("['-]", '', location)
        if isinstance(provider, Indeed):
            where = soup_base.find(id='where')['value'].strip()
        elif isinstance(provider, Monster):
            where = soup_base.find(id='location')['value'].strip()
        elif isinstance(provider, GlassDoorStatic):
            where = soup_base.find(id='sc.location')['value']

        if where.lower() == location.lower():
            count += 1

    # assert that at least one provider found the correct location
    assert count > 0
