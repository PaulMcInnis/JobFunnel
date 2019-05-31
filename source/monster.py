## Paul McInnis 2019
## scrapes data off monster.ca and pickles it

import pickle
import logging
import requests
import bs4
import lxml
import re
import os
import string
from math import ceil
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from config.settings import MASTERLIST_HEADER

# the maximum monster search results per page
monster_max_results_per_page = 25

def scrape_monster_to_pickle(jobpy_obj):
    ## scrape a page of monster results to a pickle
    logging.info('jobpy monster to pickle running @ : ' + jobpy_obj.date_string)

    # form the query string
    for i, s in enumerate(jobpy_obj.search_terms['keywords']):
        if i == 0:
            query = s
        else:
            query += '-' + s

    # build the job search URL
    search = 'https://www.monster.{0}/jobs/search/?q={1}&where={2}__2C-{3}' \
             '&intcid=skr_navigation_nhpso_searchMain&rad={4}&where={2}__2c-{3}'.format(
        jobpy_obj.search_terms['region']['domain'],
        query,
        jobpy_obj.search_terms['region']['city'],
        jobpy_obj.search_terms['region']['province'],
        jobpy_obj.search_terms['region']['radius'])

    # get the HTML data, initialize bs4 with lxml
    request_HTML = requests.get(search)
    soup_base = bs4.BeautifulSoup(request_HTML.text, jobpy_obj.bs4_parser)

    # scrape total number of results, and calculate the # pages needed
    num_results = soup_base.find('h2', 'figure').text.strip()
    num_results = re.sub("\(", "", num_results)
    num_results = re.sub("[a-zA-Z ]*\)", "", num_results)
    num_results = int(num_results)
    logging.info('Found {0} monster results for query={1}'.format(num_results, query))

    # scrape soups for all the pages containing jobs it found
    list_of_job_soups = []
    pages = int(ceil(num_results / monster_max_results_per_page))
    page_url = '{0}&start={1}'.format(search, pages)
    logging.info('getting monster pages 1 to {0} : {1}'.format(pages, page_url))
    jobs = bs4.BeautifulSoup(requests.get(page_url).text,
                             jobpy_obj.bs4_parser).find_all('div',
                                                       attrs={
                                                           'class': 'flex-row'})
    list_of_job_soups.extend(jobs)