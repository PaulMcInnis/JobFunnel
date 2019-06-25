## scrapes data off glassdoor.ca and pickles it

import pickle
import logging
import requests
import bs4
import re
import os
import sys
from math import ceil

from .config.settings import MASTERLIST_HEADER
from .tools.tools import filter_non_printables
from .tools.tools import post_date_from_relative_post_age

sys.path.append('../')

# the maximum monster search results per page
glassdoor_max_results_per_page = 30


def convert_glassdoor_radius(radius):
    """function that converts the user input radius to an available glassdoor radius"""
    # glassdoor only accepts discrete radius values of 10, 20, 30, 50 and 100 kilometers
    if radius < 10:
        radius = 0
    elif radius >= 10 and radius < 20:
        radius = 10
    elif radius >= 20 and radius < 30:
        radius = 20
    elif radius >= 30 and radius < 50:
        radius = 30
    elif radius >= 50 and radius < 100:
        radius = 50
    elif radius >= 100:
        radius = 100

    glassdoor_radius = {
        0: 0,
        10: 6,
        20: 12,
        30: 19,
        50: 31,
        100: 62
    }

    return glassdoor_radius[radius]


def scrape_glassdoor_to_pickle(jobpy_obj):
    """function that scrapes job posting from glassdoor and pickles it"""
    try:
        ## scrape a page of monster results to a pickle
        logging.info(
            'jobpy glassdoor to pickle running @ : ' + jobpy_obj.date_string)

        # form the query string
        for i, s in enumerate(jobpy_obj.search_terms['keywords']):
            if i == 0:
                query = s
            else:
                query += '-' + s

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                jobpy_obj.search_terms['region']['domain']),
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/51.0.2704.79 Chrome/51.0.2704.79 Safari/537.36',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

        location_headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.01',
            'accept-encoding': 'gzip, deflate, sdch, br',
            'accept-language': 'en-GB,en-US;q=0.8,en;q=0.6',
            'referer': 'https://www.glassdoor.{0}/'.format(
                jobpy_obj.search_terms['region']['domain']),
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/51.0.2704.79 Chrome/51.0.2704.79 Safari/537.36',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }

        data = {'term': jobpy_obj.search_terms['region']['city'],
                'maxLocationsToReturn': 10}

        location_url = 'https://www.glassdoor.co.in/findPopularLocationAjax.htm?'

        # get the location id for search location
        location_response = requests.post(location_url,
                                          headers=location_headers,
                                          data=data).json()
        place_id = location_response[0]['locationId']
        job_listing_url = 'https://www.glassdoor.{0}/Job/jobs.htm'.format(
            jobpy_obj.search_terms['region']['domain'])
        # form data to get job results
        data = {
            'clickSource': 'searchBtn',
            'sc.keyword': query,
            'locT': 'C',
            'locId': place_id,
            'jobType': '',
            'radius': convert_glassdoor_radius(
                jobpy_obj.search_terms['region']['radius'])
        }

        # get the HTML data, initialize bs4 with lxml
        request_HTML = requests.post(job_listing_url, headers=headers,
                                     data=data)
        soup_base = bs4.BeautifulSoup(request_HTML.text, jobpy_obj.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find('p',
                                     attrs={'class', 'jobsCount'}).text.strip()
        num_results = re.sub('[a-zA-Z ]*', '', num_results)
        num_results = re.sub(',', '', num_results)
        num_results = int(num_results)
        logging.info(
            'Found {0} glassdoor results for query={1}'.format(num_results,
                                                               query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / glassdoor_max_results_per_page))

        # add the jobs shown in soup base
        jobs = soup_base.find_all('li', attrs={'class', 'jl'})
        list_of_job_soups.extend(jobs)

        for page in range(1, pages):
            page_url = 'https://www.glassdoor.{0}{1}'.format(
                jobpy_obj.search_terms['region']['domain'],
                soup_base.find('li', attrs={'class', 'next'}).find('a').get(
                    'href'))
            logging.info(
                'getting glassdoor next page {0} : {1}'.format(page, page_url))
            jobs = bs4.BeautifulSoup(requests.get(page_url).text,
                                     jobpy_obj.bs4_parser).find_all('li',
                                                                    attrs={
                                                                        'class',
                                                                        'jl'})
            list_of_job_soups.extend(jobs)

        # make a dict of job postings from the listing briefs
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('div', attrs={'class',
                                                    'titleContainer'}).text.strip()
                # @TODO if a compnay name includes a '–' it may be mistaken in re.sub
                job['company'] = re.sub(' – [a-zA-Z ]*', '', str(
                    s.find('div', attrs={'class', 'flexbox empLoc'}).find(
                        'div').text.strip()))
                job['location'] = s.get('data-job-loc')
            except AttributeError:
                continue

            # no blurb is available in glassdoor job soups
            job['blurb'] = ''

            # no date is available in glassdoor job soups
            job['date'] = ''

            try:
                job['id'] = s.get('data-id')
                job['link'] = 'https://www.glassdoor.{0}{1}'.format(
                    jobpy_obj.search_terms['region']['domain'],
                    s.find('div', attrs={'class', 'logoWrap'}).find('a').get(
                        'href'))
            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            # traverse the job link to extract the blurb and date
            search = job['link']
            request_HTML = requests.post(search, headers=location_headers)
            job_link_soup = bs4.BeautifulSoup(request_HTML.text,
                                              jobpy_obj.bs4_parser)

            try:
                job['blurb'] = job_link_soup.find(
                    id='JobDescriptionContainer').text.strip()
            except AttributeError:
                job['blurb'] = ''

            try:
                job['date'] = job_link_soup.find('span', attrs={'class',
                                                                'minor nowrap'}).text.strip()
            except AttributeError:
                job['date'] = ''

            filter_non_printables(job)
            post_date_from_relative_post_age(job)

            # key by id
            jobpy_obj.daily_scrape_dict[str(job['id'])] = job

        # save the resulting jobs dict as a pickle file
        pickle_name = 'jobs_{0}.pkl'.format(jobpy_obj.date_string)
        pickle.dump(jobpy_obj.daily_scrape_dict,
                    open(os.path.join(jobpy_obj.pickles_dir, pickle_name),
                         'wb'))
        logging.info(
            'glassdoor pickle file successfully dumped to ' + pickle_name)

    except Exception as e:
        logging.info('scrape glassdoor to pickle failed @ : ' + str(e))
        pass
