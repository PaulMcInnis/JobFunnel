## scrapes data off indeed.ca and pickles it

import pickle
import logging
import requests
import bs4
import re
import os
import sys
from math import ceil
from config.settings import MASTERLIST_HEADER
from tools.tools import filter_non_printables
from tools.tools import post_date_from_relative_post_age

sys.path.append('../')

# the maximum indeed search results per page
indeed_max_results_per_page = 50


def scrape_indeed_to_pickle(jobpy_obj):
    """function that scrapes job posting from indeed and pickles it"""
    try:
        ## scrape a page of indeed results to a pickle
        logging.info(
            'jobpy indeed to pickle running @ : ' + jobpy_obj.date_string)

        # form the query string
        for i, s in enumerate(jobpy_obj.search_terms['keywords']):
            if i == 0:
                query = s
            else:
                query += '+' + s

        # build the job search URL
        search = 'http://www.indeed.{0}/jobs?q={1}&l={2}%2C+{3}&radius={4}' \
                 '&limit={5}&filter={6}'.format(
            jobpy_obj.search_terms['region']['domain'],
            query,
            jobpy_obj.search_terms['region']['city'],
            jobpy_obj.search_terms['region']['province'],
            jobpy_obj.search_terms['region']['radius'],
            indeed_max_results_per_page,
            int(jobpy_obj.similar_results))

        # get the HTML data, initialize bs4 with lxml
        request_HTML = requests.get(search)
        soup_base = bs4.BeautifulSoup(request_HTML.text, jobpy_obj.bs4_parser)

        # scrape total number of results, and calculate the # pages needed
        num_results = soup_base.find(id='searchCount').contents[0].strip()
        num_results = re.sub('.*of ', '', num_results)
        num_results = re.sub(',', '', num_results)
        num_results = re.sub('jobs.*', '', num_results)
        num_results = int(num_results)
        logging.info(
            'Found {0} indeed results for query={1}'.format(num_results, query))

        # scrape soups for all the pages containing jobs it found
        list_of_job_soups = []
        pages = int(ceil(num_results / indeed_max_results_per_page))
        for page in range(0, pages):
            page_url = '{0}&start={1}'.format(search,
                                              int(
                                                  page * indeed_max_results_per_page))
            logging.info('getting indeed page {0} : {1}'.format(page, page_url))
            jobs = bs4.BeautifulSoup(requests.get(page_url).text,
                                     jobpy_obj.bs4_parser).find_all('div',
                                                                    attrs={
                                                                        'data-tn-component': 'organicJob'})
            list_of_job_soups.extend(jobs)

        # make a dict of job postings from the listing briefs
        for s in list_of_job_soups:
            # init dict to store scraped data
            job = dict([(k, '') for k in MASTERLIST_HEADER])

            # scrape the post data
            job['status'] = 'new'
            try:
                # jobs should at minimum have a title, company and location
                job['title'] = s.find('a', attrs={
                    'data-tn-element': 'jobTitle'}).text.strip()
                job['company'] = s.find('span',
                                        attrs={'class': 'company'}).text.strip()
                job['location'] = s.find('span', attrs={
                    'class': 'location'}).text.strip()
            except AttributeError:
                continue

            try:
                job['blurb'] = s.find('div',
                                      attrs={'class': 'summary'}).text.strip()
            except AttributeError:
                job['blurb'] = ''

            try:
                job['date'] = s.find('span',
                                     attrs={'class': 'date'}).text.strip()
            except AttributeError:
                job['date'] = ''

            try:
                job['id'] = re.findall(r'id=\"sj_[a-zA-Z0-9]*\"', str(
                    s.find('a', attrs={
                        'class': 'sl resultLink save-job-link'})))[0]
                job['id'] = re.sub('id=\"sj_', '', job['id'])
                job['id'] = re.sub('\"', '', job['id'])
                job['link'] = 'http://www.indeed.{0}/viewjob?jk={1}'.format(
                    jobpy_obj.search_terms['region']['domain'], job['id'])
            except (AttributeError, IndexError):
                job['id'] = ''
                job['link'] = ''

            filter_non_printables(job)
            post_date_from_relative_post_age(job)

            # key by id
            jobpy_obj.daily_scrape_dict[str(job['id'])] = job

        # save the resulting jobs dict as a pickle file
        pickle_name = 'jobs_{0}.pkl'.format(jobpy_obj.date_string)
        pickle.dump(jobpy_obj.daily_scrape_dict,
                    open(os.path.join(jobpy_obj.pickles_dir, pickle_name),
                         'wb'))
        logging.info('indeed pickle file successfully dumped to ' + pickle_name)

    except Exception as e:
        logging.info('scrape indeed to pickle failed @ : ' + str(e))
        pass
